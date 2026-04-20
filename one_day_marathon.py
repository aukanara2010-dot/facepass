#!/usr/bin/env python3
"""
one_day_marathon.py — Суточный марафон стресс-теста FacePass.

Скрипт выполняет полный pre-flight check (Redis, S3, PostgreSQL, диск,
права на запись в logs/) и затем запускает stress_progression_v2.py
в фоновом режиме с логированием в logs/stress_test/.

Запуск:
    cd ~/facepass
    python one_day_marathon.py

Для фонового запуска:
    nohup python one_day_marathon.py > logs/stress_test/marathon_$(date +%Y%m%d_%H%M%S).log 2>&1 &
    echo $! > logs/stress_test/marathon.pid
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
# 1. Загрузка .env ДО любых импортов из core/
# ---------------------------------------------------------------------------
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Стандартные импорты (после загрузки .env)
# ---------------------------------------------------------------------------
import asyncio
import datetime
import glob
import logging
import shutil
import subprocess
import time

import boto3
from botocore.client import Config
import redis
import sqlalchemy as sa

from core.config import get_settings

# ---------------------------------------------------------------------------
# 3. Логирование
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(PROJECT_ROOT, "logs", "stress_test")
os.makedirs(LOG_DIR, exist_ok=True)

_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
_log_file = os.path.join(LOG_DIR, f"marathon_{_ts}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("marathon")

# ---------------------------------------------------------------------------
# 4. Константы
# ---------------------------------------------------------------------------
MIN_FREE_DISK_GB = 5          # Минимум свободного места на диске
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "test_images")
FALLBACK_IMAGE = os.path.join(PROJECT_ROOT, "test.jpg")
STRESS_SCRIPT = os.path.join(PROJECT_ROOT, "plans", "stress_progression_v2.py")
PID_FILE = os.path.join(LOG_DIR, "marathon.pid")

# ---------------------------------------------------------------------------
# 5. Health-check функции
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    logger.info("")
    logger.info("=" * 60)
    logger.info("  %s", title)
    logger.info("=" * 60)


def check_write_permissions() -> bool:
    """Проверяет права на запись в logs/stress_test/."""
    _section("CHECK: Write permissions → logs/stress_test/")
    test_file = os.path.join(LOG_DIR, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        logger.info("  ✅ Write permissions OK (%s)", LOG_DIR)
        return True
    except OSError as e:
        logger.error("  ❌ Cannot write to %s: %s", LOG_DIR, e)
        logger.error("     Fix: sudo chown -R $(whoami):$(whoami) %s && chmod -R 755 %s", LOG_DIR, LOG_DIR)
        return False


def check_test_images() -> bool:
    """Проверяет наличие тестовых изображений."""
    _section("CHECK: Test images")
    images = []
    for pat in [
        os.path.join(TEST_IMAGES_DIR, "*.jpg"),
        os.path.join(TEST_IMAGES_DIR, "*.jpeg"),
        os.path.join(TEST_IMAGES_DIR, "*.png"),
    ]:
        images.extend(glob.glob(pat))

    if images:
        logger.info("  ✅ Found %d images in %s", len(images), TEST_IMAGES_DIR)
        for img in sorted(images):
            size_kb = os.path.getsize(img) // 1024
            logger.info("     • %s  (%d KB)", os.path.basename(img), size_kb)
        if len(images) < 5:
            logger.warning(
                "  ⚠  Only %d image(s). For a realistic test add 5-10 different face photos "
                "to %s/", len(images), TEST_IMAGES_DIR
            )
        return True

    if os.path.exists(FALLBACK_IMAGE):
        logger.warning(
            "  ⚠  test_images/ is empty — will use single fallback %s. "
            "DB indexes won't be stressed properly.", FALLBACK_IMAGE
        )
        return True

    logger.error(
        "  ❌ No test images found. Put face photos into %s/ or place test.jpg at %s",
        TEST_IMAGES_DIR, FALLBACK_IMAGE,
    )
    return False


def check_redis(settings) -> bool:
    """Проверяет соединение с Redis."""
    _section("CHECK: Redis")
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=5,
            decode_responses=True,
        )
        pong = r.ping()
        queue_len = r.llen("celery")
        logger.info(
            "  ✅ Redis OK  host=%s:%s  PING=%s  celery queue=%d",
            settings.REDIS_HOST, settings.REDIS_PORT, pong, queue_len,
        )
        if queue_len > 0:
            logger.warning(
                "  ⚠  Celery queue is not empty (%d tasks). "
                "Consider running: celery -A core.celery_app purge -f", queue_len
            )
        return True
    except Exception as e:
        logger.error("  ❌ Redis connection failed: %s", e)
        logger.error(
            "     Check REDIS_HOST=%s REDIS_PORT=%s in .env",
            settings.REDIS_HOST, settings.REDIS_PORT,
        )
        return False


def check_s3(settings) -> bool:
    """Проверяет соединение с S3 (создаёт и удаляет тестовый объект)."""
    _section("CHECK: S3")
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version='s3',       # Beget S3 требует SigV2 для PutObject
                connect_timeout=30,
                read_timeout=30,
                s3={'addressing_style': 'path'},
            ),
        )
        test_key = f"{settings.S3_ENV_PREFIX}/health_check/marathon_test.txt"
        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=test_key,
            Body=b"FacePass marathon health check",
        )
        head = s3.head_object(Bucket=settings.S3_BUCKET, Key=test_key)
        s3.delete_object(Bucket=settings.S3_BUCKET, Key=test_key)
        status = head["ResponseMetadata"]["HTTPStatusCode"]
        logger.info(
            "  ✅ S3 OK  endpoint=%s  bucket=%s  prefix=%s  (HTTP %d)",
            settings.S3_ENDPOINT, settings.S3_BUCKET, settings.S3_ENV_PREFIX, status,
        )
        return True
    except Exception as e:
        logger.error("  ❌ S3 connection failed: %s", e)
        logger.error(
            "     Check S3_ENDPOINT=%s S3_BUCKET=%s in .env",
            settings.S3_ENDPOINT, settings.S3_BUCKET,
        )
        return False


def check_postgres(settings) -> bool:
    """Проверяет соединение с PostgreSQL."""
    _section("CHECK: PostgreSQL")
    try:
        dsn = (
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        eng = sa.create_engine(dsn, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with eng.connect() as conn:
            result = conn.execute(sa.text("SELECT 1"))
            val = result.scalar()

            # Проверяем наличие таблицы face_embeddings
            table_exists = conn.execute(sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'face_embeddings')"
            )).scalar()

            row_count = 0
            if table_exists:
                row_count = conn.execute(
                    sa.text("SELECT COUNT(*) FROM face_embeddings")
                ).scalar() or 0

        logger.info(
            "  ✅ PostgreSQL OK  host=%s:%s  db=%s  SELECT 1=%s  "
            "face_embeddings=%s  rows=%d",
            settings.POSTGRES_HOST, settings.POSTGRES_PORT,
            settings.POSTGRES_DB, val,
            "exists" if table_exists else "NOT FOUND",
            row_count,
        )
        if not table_exists:
            logger.warning(
                "  ⚠  Table face_embeddings does not exist. "
                "Run: python scripts/init_db.py"
            )
        eng.dispose()
        return True
    except Exception as e:
        logger.error("  ❌ PostgreSQL connection failed: %s", e)
        logger.error(
            "     Check POSTGRES_HOST=%s POSTGRES_PORT=%s POSTGRES_DB=%s in .env",
            settings.POSTGRES_HOST, settings.POSTGRES_PORT, settings.POSTGRES_DB,
        )
        return False


def check_disk_space() -> bool:
    """Проверяет свободное место на диске."""
    _section("CHECK: Disk space")
    usage = shutil.disk_usage(PROJECT_ROOT)
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    used_pct = (usage.used / usage.total) * 100

    if free_gb >= MIN_FREE_DISK_GB:
        logger.info(
            "  ✅ Disk OK  free=%.1f GB / total=%.1f GB  used=%.0f%%",
            free_gb, total_gb, used_pct,
        )
        return True
    else:
        logger.error(
            "  ❌ Not enough disk space: %.1f GB free (need >= %d GB)",
            free_gb, MIN_FREE_DISK_GB,
        )
        return False


def check_python_deps() -> bool:
    """Проверяет наличие необходимых Python-библиотек."""
    _section("CHECK: Python dependencies")
    required = {
        "boto3": "boto3",
        "psutil": "psutil",
        "redis": "redis",
        "rich": "rich",
        "celery": "celery",
        "sqlalchemy": "sqlalchemy",
    }
    missing = []
    for display_name, module_name in required.items():
        try:
            __import__(module_name)
            logger.info("  ✅ %-15s OK", display_name)
        except ImportError:
            logger.error("  ❌ %-15s MISSING  →  pip install %s", display_name, display_name)
            missing.append(display_name)

    if missing:
        logger.error("  Install missing packages: pip install %s", " ".join(missing))
        return False
    return True


# ---------------------------------------------------------------------------
# 6. Полный pre-flight check
# ---------------------------------------------------------------------------

def run_preflight_checks() -> bool:
    """Запускает все проверки. Возвращает True если всё OK."""
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║       FacePass — Pre-flight Health Check                 ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("  Project root : %s", PROJECT_ROOT)
    logger.info("  .env file    : %s", _env_path)
    logger.info("  Log file     : %s", _log_file)
    logger.info("  Time         : %s", datetime.datetime.now().isoformat())

    settings = get_settings()

    checks = [
        ("Write permissions", check_write_permissions),
        ("Test images",       check_test_images),
        ("Python deps",       check_python_deps),
        ("Redis",             lambda: check_redis(settings)),
        ("S3",                lambda: check_s3(settings)),
        ("PostgreSQL",        lambda: check_postgres(settings)),
        ("Disk space",        check_disk_space),
    ]

    results = {}
    for name, fn in checks:
        try:
            results[name] = fn()
        except Exception as e:
            logger.error("  ❌ %s check raised exception: %s", name, e)
            results[name] = False

    # Итоговая таблица
    _section("SUMMARY")
    all_ok = True
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        logger.info("  %s  %s", icon, name)
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("")
        logger.info("  🚀 All checks passed — ready to start the marathon!")
    else:
        logger.error("")
        logger.error("  ⛔ Some checks FAILED. Fix the issues above before running the test.")

    return all_ok


# ---------------------------------------------------------------------------
# 7. Запуск стресс-теста
# ---------------------------------------------------------------------------

def launch_stress_test() -> None:
    """Запускает stress_progression_v2.py и ждёт его завершения."""
    _section("LAUNCH: stress_progression_v2.py")

    python_bin = sys.executable
    logger.info("  Python  : %s", python_bin)
    logger.info("  Script  : %s", STRESS_SCRIPT)
    logger.info("  Started : %s", datetime.datetime.now().isoformat())

    if not os.path.exists(STRESS_SCRIPT):
        logger.error("  ❌ Script not found: %s", STRESS_SCRIPT)
        sys.exit(1)

    # Сохраняем PID для возможной остановки
    proc = subprocess.Popen(
        [python_bin, STRESS_SCRIPT],
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
    )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    logger.info("  PID     : %d  (saved to %s)", proc.pid, PID_FILE)
    logger.info("  Stop    : kill $(cat %s)", PID_FILE)

    try:
        proc.wait()
    except KeyboardInterrupt:
        logger.info("  Interrupted — sending SIGTERM to PID %d", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

    logger.info("  Finished: %s  returncode=%d", datetime.datetime.now().isoformat(), proc.returncode)


# ---------------------------------------------------------------------------
# 8. Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ok = run_preflight_checks()
    if not ok:
        logger.error("Pre-flight checks failed. Aborting marathon.")
        sys.exit(1)

    logger.info("")
    logger.info("Waiting 5 seconds before launch (Ctrl+C to abort)…")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Aborted by user.")
        sys.exit(0)

    launch_stress_test()


if __name__ == "__main__":
    main()
