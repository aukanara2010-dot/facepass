#!/usr/bin/env python3
"""
stress_progression_v2.py — Ступенчатый стресс-тест FacePass.

Запуск:
    cd ~/facepass
    python plans/stress_progression_v2.py

Требования:
    pip install boto3 psutil redis pandas rich celery sqlalchemy
"""

# ---------------------------------------------------------------------------
# 0. Авто-установка критичных зависимостей (psutil, rich) до всего остального
# ---------------------------------------------------------------------------
import sys
import subprocess

def _ensure_deps() -> None:
    """Проверяет наличие psutil и rich; при отсутствии устанавливает через pip."""
    missing = []
    for pkg in ("psutil", "rich"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[deps] Missing packages: {missing}. Installing via pip...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
                check=True,
            )
            print(f"[deps] Successfully installed: {missing}")
        except subprocess.CalledProcessError as _e:
            print(
                f"[deps] Auto-install failed: {_e}\n"
                f"       Run manually:  pip install {' '.join(missing)}"
            )

_ensure_deps()

# ---------------------------------------------------------------------------
# Загрузка .env ДО любых импортов из core/
# ---------------------------------------------------------------------------
import os

# Добавляем корень проекта в sys.path, чтобы работали импорты core.*
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Загружаем переменные окружения из .env
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())
    print(f"[env] Loaded variables from {_env_path}")
else:
    print(f"[env] WARNING: .env not found at {_env_path}")

# ---------------------------------------------------------------------------
# Стандартные импорты
# ---------------------------------------------------------------------------
import asyncio
import boto3
from botocore.client import Config
import csv
import datetime
import glob
import logging
import platform
import psutil
import random
import statistics
import string
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import redis
import sqlalchemy as sa
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.orm import sessionmaker

# Импорт задачи Celery и конфигурации
from services.tasks import sync_s3_photos_task
from core.config import get_settings
from core.database import engine

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn, Progress
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich library not found. Using standard console output.")

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------
STEP_MINUTES = 60                   # Шаг увеличения нагрузки (минуты)
POINT_INTERVAL_SECONDS = 1.08       # Интервал между задачами для одной точки
METRICS_INTERVAL_MINUTES = 5        # Интервал сбора метрик
MAX_POINTS = 18                     # Максимальное количество точек
POINTS_INCREMENT = 2                # Прирост точек на каждом шаге
TARGET_PHOTOS_PER_POINT = 80_000    # Целевое кол-во фото на точку

# Директория с тестовыми изображениями (несколько разных лиц)
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "test_images")
# Fallback — одиночный файл
FALLBACK_IMAGE = os.path.join(PROJECT_ROOT, "test.jpg")

S3_PREFIX = "stress_test"
CSV_REPORT_PATH = os.path.join(PROJECT_ROOT, "logs", "stress_test", "stress_results.csv")

# Критерии остановки
MAX_QUEUE_SIZE = 3_000
MAX_RAM_PERCENT = 90
MAX_RUNTIME_INCREASE_PERCENT = 50

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(PROJECT_ROOT, "logs", "stress_test")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, f"stress_v2_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("stress_v2")


# ---------------------------------------------------------------------------
# Вспомогательная функция: список тестовых изображений
# ---------------------------------------------------------------------------
def _get_test_images() -> List[str]:
    """Возвращает список путей к тестовым изображениям.

    Сначала ищет файлы в TEST_IMAGES_DIR, затем падает на FALLBACK_IMAGE.
    """
    patterns = [
        os.path.join(TEST_IMAGES_DIR, "*.jpg"),
        os.path.join(TEST_IMAGES_DIR, "*.jpeg"),
        os.path.join(TEST_IMAGES_DIR, "*.png"),
    ]
    images: List[str] = []
    for pat in patterns:
        images.extend(glob.glob(pat))

    if images:
        logger.info("Found %d test images in %s", len(images), TEST_IMAGES_DIR)
        return sorted(images)

    if os.path.exists(FALLBACK_IMAGE):
        logger.warning(
            "test_images/ not found or empty — using single fallback image %s. "
            "For a realistic test place 5-10 different face photos in test_images/",
            FALLBACK_IMAGE,
        )
        return [FALLBACK_IMAGE]

    raise FileNotFoundError(
        f"No test images found. Put face photos into {TEST_IMAGES_DIR}/ "
        f"or place test.jpg at {FALLBACK_IMAGE}"
    )


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------
class StressTestRunner:
    """Управляет ступенчатым стресс-тестом FacePass."""

    def __init__(self) -> None:
        logger.info("Initializing StressTestRunner")

        self.settings = get_settings()

        # Список тестовых изображений (разные лица → разные векторы)
        self.test_images: List[str] = _get_test_images()
        logger.info("Will rotate among %d test images per upload", len(self.test_images))

        # S3 — Beget S3 требует SigV2 (signature_version='s3') для PutObject
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.settings.S3_ENDPOINT,
            aws_access_key_id=self.settings.S3_ACCESS_KEY,
            aws_secret_access_key=self.settings.S3_SECRET_KEY,
            region_name=self.settings.S3_REGION,
            config=Config(
                signature_version='s3',       # Fix XAmzContentSHA256Mismatch
                connect_timeout=120,
                read_timeout=120,
                s3={'addressing_style': 'path'},
            ),
        )

        # Redis
        self.redis_client = redis.Redis(
            host=self.settings.REDIS_HOST,
            port=self.settings.REDIS_PORT,
            db=self.settings.REDIS_DB,
            password=self.settings.REDIS_PASSWORD,
            decode_responses=True,
        )

        # БД
        self.engine = engine
        self.Session = sessionmaker(bind=engine)

        # Celery (только для инспекции очереди)
        broker = self.settings.CELERY_BROKER_URL or (
            f"redis://:{self.settings.REDIS_PASSWORD}@{self.settings.REDIS_HOST}:"
            f"{self.settings.REDIS_PORT}/{self.settings.REDIS_DB}"
            if self.settings.REDIS_PASSWORD
            else f"redis://{self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}/{self.settings.REDIS_DB}"
        )
        self.celery_app = Celery("facepass", broker=broker)

        # Состояние теста
        self.current_points: int = 0
        self.point_threads: Dict[int, threading.Thread] = {}
        self.stop_event = threading.Event()
        self.task_runtimes: List[float] = []
        self.baseline_runtime: Optional[float] = None
        self.last_disk_io = None
        self.last_disk_io_time: float = 0.0
        self.point_stats: Dict[int, int] = {}
        self.total_completed_tasks: int = 0
        self.start_time: Optional[datetime.datetime] = None

        # CSV
        os.makedirs(os.path.dirname(CSV_REPORT_PATH), exist_ok=True)
        self._init_csv_report()

        # Rich UI
        if RICH_AVAILABLE:
            self.console = Console()

        logger.info(
            "Runner initialized. Step=%d min, max_points=%d, images=%d",
            STEP_MINUTES, MAX_POINTS, len(self.test_images),
        )

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------
    def _init_csv_report(self) -> None:
        with open(CSV_REPORT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "points_count", "cpu_load", "ram_used", "ram_percent",
                "queue_size", "db_rows", "avg_runtime", "runtime_increase",
                "disk_read_mbps", "disk_write_mbps",
                "total_completed_tasks", "tasks_per_second",
            ])
            writer.writeheader()
        logger.info("CSV report initialised at %s", CSV_REPORT_PATH)

    def _write_csv_metrics(self, metrics: Dict) -> None:
        elapsed = (datetime.datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        tasks_per_second = self.total_completed_tasks / elapsed if elapsed > 0 else 0
        row = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_completed_tasks": self.total_completed_tasks,
            "tasks_per_second": round(tasks_per_second, 3),
            **metrics,
        }
        with open(CSV_REPORT_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writerow(row)

    # ------------------------------------------------------------------
    # DB session
    # ------------------------------------------------------------------
    @contextmanager
    def _get_db_session(self):
        session = self.Session()
        try:
            yield session
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Метрики
    # ------------------------------------------------------------------
    def _get_queue_size(self) -> int:
        try:
            return self.redis_client.llen("celery")
        except Exception as e:
            logger.warning("Cannot get queue size: %s", e)
            return 0

    def _get_db_rows_count(self) -> int:
        try:
            with self._get_db_session() as session:
                result = session.execute(sa.text("SELECT COUNT(*) FROM face_embeddings"))
                return result.scalar() or 0
        except Exception as e:
            logger.warning("Cannot get DB rows count: %s", e)
            return 0

    def _collect_metrics(self) -> Dict:
        try:
            cpu_load = psutil.cpu_percent(interval=1)
            ram_info = psutil.virtual_memory()
            ram_used_gb = ram_info.used / (1024 ** 3)
            ram_percent = ram_info.percent

            disk_io = psutil.disk_io_counters()
            if self.last_disk_io and self.last_disk_io_time:
                dt = time.time() - self.last_disk_io_time
                read_mbps = (disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 ** 2 * dt)
                write_mbps = (disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 ** 2 * dt)
            else:
                read_mbps = write_mbps = 0.0
            self.last_disk_io = disk_io
            self.last_disk_io_time = time.time()

            queue_size = self._get_queue_size()
            db_rows = self._get_db_rows_count()

            avg_runtime = 0.0
            runtime_increase = 0.0
            if self.task_runtimes:
                last_10 = self.task_runtimes[-10:]
                avg_runtime = sum(last_10) / len(last_10)
                if self.baseline_runtime:
                    runtime_increase = ((avg_runtime / self.baseline_runtime) - 1) * 100

            metrics = {
                "points_count": self.current_points,
                "cpu_load": round(cpu_load, 1),
                "ram_used": round(ram_used_gb, 2),
                "ram_percent": round(ram_percent, 1),
                "queue_size": queue_size,
                "db_rows": db_rows,
                "avg_runtime": round(avg_runtime, 2),
                "runtime_increase": round(runtime_increase, 1),
                "disk_read_mbps": round(read_mbps, 2),
                "disk_write_mbps": round(write_mbps, 2),
            }
            logger.info("Metrics: %s", metrics)
            self._write_csv_metrics(metrics)
            return metrics

        except Exception as e:
            logger.error("Error collecting metrics: %s", e)
            return {
                "points_count": self.current_points,
                "cpu_load": 0, "ram_used": 0, "ram_percent": 0,
                "queue_size": 0, "db_rows": 0, "avg_runtime": 0,
                "runtime_increase": 0, "disk_read_mbps": 0, "disk_write_mbps": 0,
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Критерии остановки
    # ------------------------------------------------------------------
    def _check_breaking_point(self, metrics: Dict) -> Tuple[bool, str]:
        if metrics["queue_size"] > MAX_QUEUE_SIZE:
            return True, f"Queue size {metrics['queue_size']} > {MAX_QUEUE_SIZE}"
        if metrics["ram_percent"] > MAX_RAM_PERCENT:
            return True, f"RAM {metrics['ram_percent']}% > {MAX_RAM_PERCENT}%"
        if metrics["runtime_increase"] > MAX_RUNTIME_INCREASE_PERCENT:
            return True, f"Runtime increase {metrics['runtime_increase']}% > {MAX_RUNTIME_INCREASE_PERCENT}%"
        return False, ""

    # ------------------------------------------------------------------
    # Загрузка изображений в S3
    # ------------------------------------------------------------------
    def _generate_session_id(self) -> str:
        return str(uuid.uuid4())

    def _upload_test_images(self, session_id: str, count: int = 5) -> bool:
        """Загружает `count` случайных изображений из test_images/ в S3.

        Каждый раз выбирает разные файлы → разные векторы → реальная нагрузка на индексы.
        """
        try:
            # Случайная выборка без повторений (или с повторениями, если count > len)
            chosen = random.choices(self.test_images, k=count)
            for i, img_path in enumerate(chosen):
                s3_key = (
                    f"{self.settings.S3_ENV_PREFIX}/{S3_PREFIX}/"
                    f"{session_id}/photo_{i + 1:03d}.jpg"
                )
                with open(img_path, "rb") as fh:
                    self.s3_client.put_object(
                        Bucket=self.settings.S3_BUCKET,
                        Key=s3_key,
                        Body=fh.read(),
                        ContentType="image/jpeg",
                    )
            logger.debug(
                "Uploaded %d images for session %s (files: %s)",
                count, session_id,
                [os.path.basename(p) for p in chosen],
            )
            return True
        except Exception as e:
            logger.error("Failed to upload images for session %s: %s", session_id, e)
            return False

    # ------------------------------------------------------------------
    # Поток одной точки нагрузки
    # ------------------------------------------------------------------
    def _run_point_process(self, point_id: int) -> None:
        logger.info("Point #%d started", point_id)
        self.point_stats[point_id] = 0
        tasks_completed = 0

        while not self.stop_event.is_set() and tasks_completed < TARGET_PHOTOS_PER_POINT:
            loop_start = time.time()
            try:
                session_id = self._generate_session_id()

                if self._upload_test_images(session_id):
                    task_start = time.time()
                    task = sync_s3_photos_task.apply_async(args=[session_id])

                    tasks_completed += 1
                    self.point_stats[point_id] = tasks_completed
                    self.total_completed_tasks += 1

                    # Асинхронно ждём завершения для замера времени
                    try:
                        task.get(timeout=180)
                        runtime = time.time() - task_start
                        self.task_runtimes.append(runtime)
                        if self.baseline_runtime is None:
                            self.baseline_runtime = runtime
                        logger.debug("Point #%d task done in %.2fs", point_id, runtime)
                    except Exception as e:
                        logger.warning("Point #%d task monitoring error: %s", point_id, e)

            except Exception as e:
                logger.error("Point #%d error: %s", point_id, e)
                time.sleep(5)
                continue

            # Строго соблюдаем интервал
            elapsed = time.time() - loop_start
            sleep_time = POINT_INTERVAL_SECONDS - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info(
            "Point #%d finished: %d/%d tasks",
            point_id, tasks_completed, TARGET_PHOTOS_PER_POINT,
        )

    # ------------------------------------------------------------------
    # Добавление точек нагрузки
    # ------------------------------------------------------------------
    def _add_points(self, count: int) -> None:
        for _ in range(count):
            self.current_points += 1
            pid = self.current_points
            t = threading.Thread(
                target=self._run_point_process,
                args=(pid,),
                name=f"point-{pid}",
                daemon=True,
            )
            self.point_threads[pid] = t
            t.start()
            logger.info("Added point #%d (total active: %d)", pid, self.current_points)

    # ------------------------------------------------------------------
    # Отображение в консоли
    # ------------------------------------------------------------------
    def _update_display(
        self, metrics: Dict, breaking_point: bool = False, reason: str = ""
    ) -> None:
        elapsed = (
            str(datetime.datetime.now() - self.start_time).split(".")[0]
            if self.start_time else "—"
        )
        if RICH_AVAILABLE:
            table = Table(title=f"FacePass Stress Test  |  elapsed {elapsed}", expand=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Limit", style="yellow")

            table.add_row("Active points", str(metrics["points_count"]), str(MAX_POINTS))
            table.add_row("CPU load", f"{metrics['cpu_load']}%", "—")
            table.add_row("RAM", f"{metrics['ram_used']} GB ({metrics['ram_percent']}%)", f"{MAX_RAM_PERCENT}%")
            table.add_row("Queue size", str(metrics["queue_size"]), str(MAX_QUEUE_SIZE))
            table.add_row("DB rows", str(metrics["db_rows"]), "—")
            table.add_row("Avg task time", f"{metrics['avg_runtime']}s", "—")
            table.add_row("Runtime increase", f"{metrics['runtime_increase']}%", f"{MAX_RUNTIME_INCREASE_PERCENT}%")
            table.add_row("Disk R/W", f"{metrics['disk_read_mbps']}/{metrics['disk_write_mbps']} MB/s", "—")
            table.add_row("Total tasks sent", str(self.total_completed_tasks), "—")

            self.console.print(table)
            if breaking_point:
                self.console.print(f"[bold red]⚠ Breaking point:[/bold red] {reason}")
        else:
            print(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                f"points={metrics['points_count']} cpu={metrics['cpu_load']}% "
                f"ram={metrics['ram_percent']}% queue={metrics['queue_size']} "
                f"db_rows={metrics['db_rows']} avg_rt={metrics['avg_runtime']}s "
                f"rt_inc={metrics['runtime_increase']}% tasks={self.total_completed_tasks}"
            )
            if breaking_point:
                print(f"  *** BREAKING POINT: {reason} ***")

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    async def run(self) -> None:
        logger.info("=== Stress test started ===")
        self.start_time = datetime.datetime.now()

        try:
            # Стартуем с 1 точки
            self._add_points(1)

            next_step_time = time.time() + STEP_MINUTES * 60
            next_metrics_time = time.time() + METRICS_INTERVAL_MINUTES * 60

            breaking_point_reached = False
            breaking_reason = ""

            while self.current_points <= MAX_POINTS and not breaking_point_reached:
                now = time.time()

                # Шаг прогрессии
                if now >= next_step_time:
                    if self.current_points < MAX_POINTS:
                        to_add = min(POINTS_INCREMENT, MAX_POINTS - self.current_points)
                        self._add_points(to_add)
                    next_step_time = now + STEP_MINUTES * 60

                # Сбор метрик
                if now >= next_metrics_time:
                    metrics = self._collect_metrics()
                    breaking_point_reached, breaking_reason = self._check_breaking_point(metrics)
                    self._update_display(metrics, breaking_point_reached, breaking_reason)
                    next_metrics_time = now + METRICS_INTERVAL_MINUTES * 60

                await asyncio.sleep(1)

            # Финальные метрики
            final_metrics = self._collect_metrics()
            self._update_display(final_metrics, breaking_point_reached, breaking_reason)

            if breaking_point_reached:
                logger.info("Breaking point reached: %s", breaking_reason)
            else:
                logger.info("Stress test completed — reached maximum %d points", MAX_POINTS)

        except KeyboardInterrupt:
            logger.info("Test interrupted by user (Ctrl+C)")

        except Exception as e:
            logger.error("Unhandled error in stress test: %s", e, exc_info=True)

        finally:
            self.stop_event.set()
            logger.info(
                "=== Test finished. Points reached: %d. Total tasks: %d. Results: %s ===",
                self.current_points, self.total_completed_tasks, CSV_REPORT_PATH,
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    runner = StressTestRunner()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
