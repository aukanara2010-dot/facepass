# Дизайн скрипта stress_progression_v2.py

## Обзор

Скрипт `stress_progression_v2.py` предназначен для ступенчатого тестирования производительности системы FacePass путем постепенного увеличения нагрузки и мониторинга ключевых метрик системы.

## Функциональные требования

- Запуск из корня ~/facepass внутри venv
- Импорт задачи Celery для синхронизации S3: `from services.tasks import sync_s3_photos_task`
- Ступенчатая прогрессия нагрузки: начиная с 1 точки, увеличение на 2 точки каждые `STEP_MINUTES` (60 минут)
- Максимум: 18 точек (одна "точка" = 1 вызов задачи каждые 1.08 секунд)
- Автоматическое завершение при достижении критериев остановки (breaking point)
- Создание CSV-отчета с метриками
- Визуальное представление процесса и статуса с помощью библиотеки Rich (опционально)

## Структура скрипта

### Импорты

```python
#!/usr/bin/env python3
import asyncio
import boto3
import csv
import datetime
import logging
import os
import platform
import psutil
import random
import redis
import statistics
import string
import sys
import threading
import time
import uuid
from typing import Dict, List, Tuple
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Импорт задачи Celery
from services.tasks import sync_s3_photos_task

# Импорт конфигурации
from core.config import get_settings
from core.database import get_db
from celery.result import AsyncResult
from celery import Celery

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TaskProgressColumn
    from rich.live import Live
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich library not found. Using standard console output.")
```

### Константы

```python
# Константы для тестирования
STEP_MINUTES = 60  # Шаг увеличения нагрузки (в минутах)
POINT_INTERVAL_SECONDS = 1.08  # Интервал между запусками задач для одной точки
METRICS_INTERVAL_MINUTES = 5  # Интервал сбора метрик
MAX_POINTS = 18  # Максимальное количество точек
POINTS_INCREMENT = 2  # Увеличение количества точек на каждом шаге
SAMPLE_IMAGE_PATH = "test.jpg"  # Путь к тестовому изображению
S3_PREFIX = "stress_test"  # Префикс для тестовых данных в S3
CSV_REPORT_PATH = "stress_results.csv"  # Путь к CSV-отчету
TARGET_PHOTOS_PER_POINT = 80000  # Целевое количество фото на точку

# Критерии остановки
MAX_QUEUE_SIZE = 3000
MAX_RAM_PERCENT = 90
MAX_RUNTIME_INCREASE_PERCENT = 50
```

### Класс StressTestRunner

Основной класс, который управляет всем процессом тестирования:

```python
class StressTestRunner:
    def __init__(self):
        """Инициализация StressTestRunner"""
        # Инициализация логгера, подключений к Redis, S3, БД
        # Инициализация отслеживаемых метрик и состояния
        
    def _create_layout(self) -> Layout:
        """Создание макета для Rich UI"""
        
    def _init_csv_report(self):
        """Инициализация CSV-отчета"""
        
    def _write_csv_metrics(self, metrics: Dict):
        """Запись метрик в CSV-отчет"""
    
    @contextmanager
    def _get_db_session(self):
        """Контекстный менеджер для сессии БД"""
    
    def _get_queue_size(self) -> int:
        """Получение размера очереди Celery"""
    
    def _get_db_rows_count(self) -> int:
        """Получение количества записей в таблице face_embeddings"""
    
    def _generate_session_id(self) -> str:
        """Генерация уникального идентификатора сессии"""
    
    def _upload_test_images(self, session_id: str, count: int = 5) -> bool:
        """Загрузка тестовых изображений в S3"""
    
    def _run_point_process(self, point_id: int):
        """Запуск процесса для одной точки"""
    
    def _collect_metrics(self) -> Dict:
        """Сбор метрик системы"""
    
    def _check_breaking_point(self, metrics: Dict) -> Tuple[bool, str]:
        """Проверка критериев остановки теста"""
    
    def _update_display(self, metrics: Dict, breaking_point: bool = False, reason: str = ""):
        """Обновление отображения в консоли"""
    
    def _add_points(self, count: int):
        """Добавление указанного количества точек нагрузки"""
    
    async def run(self):
        """Запуск теста с прогрессией"""
```

### Основной блок

```python
async def main():
    """Основная функция"""
    runner = StressTestRunner()
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Подробная реализация ключевых методов

### Инициализация

```python
def __init__(self):
    """Инициализация StressTestRunner"""
    logger.info("Initializing stress test runner")
    
    self.settings = get_settings()
    
    # Инициализация клиента S3
    self.s3_client = boto3.client(
        's3',
        endpoint_url=self.settings.S3_ENDPOINT,
        aws_access_key_id=self.settings.S3_ACCESS_KEY,
        aws_secret_access_key=self.settings.S3_SECRET_KEY,
        region_name=self.settings.S3_REGION
    )
    
    # Инициализация клиента Redis
    self.redis_client = redis.Redis(
        host=self.settings.REDIS_HOST,
        port=self.settings.REDIS_PORT,
        db=self.settings.REDIS_DB,
        password=self.settings.REDIS_PASSWORD,
        decode_responses=True
    )
    
    # Подключение к базе данных
    from core.database import engine
    self.engine = engine
    self.Session = sessionmaker(bind=engine)
    
    # Настройка клиента Celery
    self.celery_app = Celery(
        "facepass",
        broker=self.settings.get_celery_broker_url()
    )
    
    # Подготовка для теста
    self.current_points = 0
    self.point_processes = {}  # Хранение процессов для каждой точки
    self.stop_event = threading.Event()
    self.task_runtimes = []  # Для хранения времени выполнения задач
    self.baseline_runtime = None  # Базовое время выполнения в начале теста
    self.last_metrics_time = time.time()
    
    # Счетчики для отслеживания выполненных задач для каждой точки
    self.point_stats = {}  # {point_id: tasks_completed}
    self.total_completed_tasks = 0
    
    # Подготовка CSV-отчета
    self._init_csv_report()
    
    # Для Rich UI
    if RICH_AVAILABLE:
        self.console = Console()
        self.layout = self._create_layout()
    
    logger.info(f"Stress test runner initialized with step time {STEP_MINUTES} minutes")
```

### Сбор метрик

```python
def _collect_metrics(self) -> Dict:
    """Сбор метрик системы"""
    try:
        # Системные метрики
        cpu_load = psutil.cpu_percent(interval=1)
        ram_info = psutil.virtual_memory()
        ram_used_gb = ram_info.used / (1024 * 1024 * 1024)  # Перевод в GB
        ram_percent = ram_info.percent
        
        # Метрики диска
        disk_io = psutil.disk_io_counters()
        if hasattr(self, 'last_disk_io') and self.last_disk_io:
            time_diff = time.time() - self.last_disk_io_time
            read_mbps = (disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024 * time_diff)
            write_mbps = (disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024 * time_diff)
        else:
            read_mbps = 0
            write_mbps = 0
        
        self.last_disk_io = disk_io
        self.last_disk_io_time = time.time()
        
        # Метрики очереди и БД
        queue_size = self._get_queue_size()
        db_rows_count = self._get_db_rows_count()
        
        # Время выполнения задач
        avg_runtime = 0
        runtime_increase_percent = 0
        
        if self.task_runtimes:
            # Берем последние 10 выполнений для среднего
            last_runtimes = self.task_runtimes[-10:]
            avg_runtime = sum(last_runtimes) / len(last_runtimes)
            
            # Вычисление процента увеличения времени выполнения
            if self.baseline_runtime:
                runtime_increase_percent = ((avg_runtime / self.baseline_runtime) - 1) * 100
        
        metrics = {
            'points_count': self.current_points,
            'cpu_load': cpu_load,
            'ram_used': ram_used_gb,
            'ram_percent': ram_percent,
            'queue_size': queue_size,
            'db_rows': db_rows_count,
            'avg_runtime': avg_runtime,
            'runtime_increase': runtime_increase_percent,
            'disk_read_mbps': read_mbps,
            'disk_write_mbps': write_mbps
        }
        
        logger.info(f"Metrics collected: {metrics}")
        self._write_csv_metrics(metrics)
        return metrics
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {
            'points_count': self.current_points,
            'cpu_load': 0,
            'ram_used': 0,
            'ram_percent': 0,
            'queue_size': 0,
            'db_rows': 0,
            'avg_runtime': 0,
            'runtime_increase': 0,
            'disk_read_mbps': 0,
            'disk_write_mbps': 0,
            'error': str(e)
        }
```

### Процесс запуска точки нагрузки

```python
def _run_point_process(self, point_id: int):
    """Запуск процесса для одной точки"""
    logger.info(f"Starting point process #{point_id}")
    
    # Инициализация счетчика для этой точки
    self.point_stats[point_id] = 0
    tasks_completed = 0
    
    while not self.stop_event.is_set() and tasks_completed < TARGET_PHOTOS_PER_POINT:
        try:
            # Создаем новую сессию
            session_id = self._generate_session_id()
            
            # Загружаем тестовые изображения
            if self._upload_test_images(session_id):
                # Запускаем задачу и замеряем время выполнения
                start_time = time.time()
                
                # Запуск задачи Celery
                task = sync_s3_photos_task.apply_async(args=[session_id])
                
                # Увеличиваем счетчик выполненных задач
                tasks_completed += 1
                self.point_stats[point_id] = tasks_completed
                self.total_completed_tasks += 1
                
                # Дождемся завершения задачи, чтобы измерить время выполнения
                # (опционально и может быть отключено для большего стресса)
                try:
                    task.get(timeout=180)  # Ждем до 3 минут
                    runtime = time.time() - start_time
                    self.task_runtimes.append(runtime)
                    logger.debug(f"Task completed in {runtime:.2f} seconds")
                    
                    # Установка базового времени выполнения, если это первая задача
                    if self.baseline_runtime is None:
                        self.baseline_runtime = runtime
                except Exception as e:
                    logger.warning(f"Task monitoring error: {e}")
            
            # Строго соблюдаем интервал между запусками задач
            next_start_time = start_time + POINT_INTERVAL_SECONDS
            current_time = time.time()
            if current_time < next_start_time:
                time.sleep(next_start_time - current_time)
            
        except Exception as e:
            logger.error(f"Error in point process #{point_id}: {e}")
            time.sleep(5)  # Короткая пауза при ошибке
            
    logger.info(f"Point process #{point_id} completed or stopped: {tasks_completed}/{TARGET_PHOTOS_PER_POINT} tasks")
```

### Проверка критериев остановки

```python
def _check_breaking_point(self, metrics: Dict) -> Tuple[bool, str]:
    """Проверка критериев остановки теста"""
    if metrics['queue_size'] > MAX_QUEUE_SIZE:
        reason = f"Queue size exceeded limit: {metrics['queue_size']} > {MAX_QUEUE_SIZE}"
        return True, reason
    
    if metrics['ram_percent'] > MAX_RAM_PERCENT:
        reason = f"RAM usage exceeded limit: {metrics['ram_percent']}% > {MAX_RAM_PERCENT}%"
        return True, reason
    
    if metrics['runtime_increase'] > MAX_RUNTIME_INCREASE_PERCENT:
        reason = f"Runtime increase exceeded limit: {metrics['runtime_increase']}% > {MAX_RUNTIME_INCREASE_PERCENT}%"
        return True, reason
    
    return False, ""
```

### Основной метод запуска теста

```python
async def run(self):
    """Запуск теста с прогрессией"""
    logger.info("Starting stress test progression")
    self.start_time = datetime.datetime.now()
    
    try:
        # Инициализация отображения Rich
        if RICH_AVAILABLE:
            live = Live(self.layout, refresh_per_second=1, screen=True)
            live.start()
        
        # Начинаем с одной точки
        self._add_points(1)
        
        # Начальное время для отсчета следующего шага и сбора метрик
        next_step_time = time.time() + STEP_MINUTES * 60
        next_metrics_time = time.time() + METRICS_INTERVAL_MINUTES * 60
        
        # Основной цикл теста
        breaking_point_reached = False
        breaking_reason = ""
        
        while self.current_points <= MAX_POINTS and not breaking_point_reached:
            current_time = time.time()
            
            # Проверка времени для следующего шага
            if current_time >= next_step_time:
                if self.current_points < MAX_POINTS:
                    points_to_add = min(POINTS_INCREMENT, MAX_POINTS - self.current_points)
                    self._add_points(points_to_add)
                next_step_time = current_time + STEP_MINUTES * 60
            
            # Проверка времени для сбора метрик
            if current_time >= next_metrics_time:
                metrics = self._collect_metrics()
                breaking_point_reached, breaking_reason = self._check_breaking_point(metrics)
                self._update_display(metrics, breaking_point_reached, breaking_reason)
                next_metrics_time = current_time + METRICS_INTERVAL_MINUTES * 60
            
            # Короткая пауза между итерациями
            await asyncio.sleep(1)
        
        # Завершающий сбор метрик
        final_metrics = self._collect_metrics()
        self._update_display(final_metrics, breaking_point_reached, breaking_reason)
        
        # Вывод заключения
        if breaking_point_reached:
            logger.info(f"Breaking point reached: {breaking_reason}")
            if RICH_AVAILABLE:
                self.console.print(f"[bold red]Breaking point reached:[/bold red] {breaking_reason}")
        else:
            logger.info("Stress test completed successfully with maximum points")
            if RICH_AVAILABLE:
                self.console.print("[bold green]Stress test completed successfully[/bold green] with maximum points")
    
    except KeyboardInterrupt:
        logger.info("Stress test interrupted by user")
        if RICH_AVAILABLE:
            self.console.print("[yellow]Test interrupted by user[/yellow]")
    
    except Exception as e:
        logger.error(f"Error in stress test: {e}", exc_info=True)
        if RICH_AVAILABLE:
            self.console.print(f"[bold red]Error:[/bold red] {e}")
    
    finally:
        # Завершение всех процессов
        self.stop_event.set()
        logger.info("Stopping all test processes")
        
        # Завершение Rich Live, если использовалась
        if RICH_AVAILABLE and 'live' in locals():
            live.stop()
        
        # Вывод сводки
        logger.info(f"Test summary: Reached {self.current_points} points")
        logger.info(f"Results saved to {CSV_REPORT_PATH}")
        
        if RICH_AVAILABLE:
            self.console.print(f"[bold]Test summary:[/bold] Reached {self.current_points} points")
            self.console.print(f"Results saved to {CSV_REPORT_PATH}")
```

## Расчет нагрузки и объемов

### Целевые параметры нагрузки

```python
# Константы для расчета нагрузки
TARGET_PHOTOS_PER_POINT = 80000  # Целевое количество фотографий на точку
POINT_INTERVAL_SECONDS = 1.08  # Интервал между запусками задач для одной точки
```

Каждая "точка" нагрузки в скрипте представляет собой отдельный источник задач, который:

1. **Генерирует строго одну задачу каждые 1.08 секунды**, обеспечивая предсказуемую и стабильную интенсивность.
2. **Суммарно должен сгенерировать 80,000 задач** (фотографий) до завершения теста.
3. **Прекращает работу** по достижении установленного лимита (80,000 задач).

### Расчет интенсивности нагрузки

При увеличении количества активных точек, общая интенсивность нагрузки растет пропорционально:

| Количество точек | Задач в секунду | Задач в минуту |
|------------------|-----------------|----------------|
| 1                | 0.93            | 55.6           |
| 2                | 1.85            | 111.1          |
| 5                | 4.63            | 277.8          |
| 10               | 9.26            | 555.6          |
| 18 (максимум)    | 16.67           | 1,000.0        |

### Реализация контроля нагрузки

```python
def _collect_progress_metrics(self) -> Dict:
    """Сбор метрик прогресса выполнения теста"""
    total_target = self.current_points * TARGET_PHOTOS_PER_POINT
    
    # Процент завершения для каждой точки
    point_progress = {}
    for point_id, completed in self.point_stats.items():
        progress_percent = (completed / TARGET_PHOTOS_PER_POINT) * 100
        point_progress[point_id] = progress_percent
    
    # Общий прогресс
    overall_progress = (self.total_completed_tasks / total_target) * 100 if total_target > 0 else 0
    
    # Прогнозируемое время завершения (оставшееся)
    etc = None
    if self.start_time and overall_progress > 0:
        elapsed_seconds = (datetime.datetime.now() - self.start_time).total_seconds()
        total_estimated_seconds = (elapsed_seconds / overall_progress) * 100
        remaining_seconds = total_estimated_seconds - elapsed_seconds
        
        # Форматирование в часы:минуты:секунды
        etc = str(datetime.timedelta(seconds=int(remaining_seconds)))
    
    # Расчет фактической нагрузки (задач в секунду)
    tasks_per_second = 0
    if elapsed_seconds > 0:
        tasks_per_second = self.total_completed_tasks / elapsed_seconds
    
    return {
        'total_completed': self.total_completed_tasks,
        'total_target': total_target,
        'overall_progress': overall_progress,
        'point_progress': point_progress,
        'etc': etc,  # Estimated Time to Completion
        'tasks_per_second': tasks_per_second
    }
```

### Контроль точного таймирования задач

Для обеспечения строгой интенсивности нагрузки (точно 1 задача каждые 1.08 секунды для каждой точки), скрипт использует механизм тайминга, который компенсирует задержки в исполнении:

```python
# В методе _run_point_process
start_time = time.time()
# ... выполнение задачи ...

# Строго соблюдаем интервал между запусками задач
next_start_time = start_time + POINT_INTERVAL_SECONDS
current_time = time.time()
if current_time < next_start_time:
    time.sleep(next_start_time - current_time)
```

### Критерии успешного прохождения теста

Тест считается успешно пройденным, если:

1. Все активные точки суммарно обработали свое целевое количество фотографий (80,000 × число точек).
2. Размер очереди Redis не превысил критического значения (`MAX_QUEUE_SIZE = 3000`).
3. Использование RAM не превысило критического порога (`MAX_RAM_PERCENT = 90%`).
4. Время выполнения задачи не увеличилось более чем на 50% от начального значения.

В отчете будут отображаться как достигнутые метрики нагрузки (общее количество обработанных задач), так и причины остановки теста, если какой-либо из критериев был нарушен.

### Визуализация прогресса теста

Скрипт отображает текущий прогресс теста, включая:
- Общее количество выполненных задач и целевое количество
- Процент завершения для каждой точки
- Прогнозируемое время до завершения (ETC - Estimated Time to Completion)
- Текущие значения ключевых метрик системы

## Формат CSV-файла

Файл `stress_results.csv` будет содержать следующие колонки:
- `timestamp` - Временная метка снятия метрик
- `points_count` - Количество активных точек нагрузки
- `cpu_load` - Загрузка CPU в процентах
- `ram_used` - Использованная память в гигабайтах
- `queue_size` - Размер очереди Redis
- `db_rows` - Количество строк в таблице face_embeddings
- `avg_runtime` - Среднее время выполнения задачи в секундах
- `runtime_increase` - Процент увеличения времени выполнения
- `disk_read_mbps` - Скорость чтения с диска в МБ/с
- `disk_write_mbps` - Скорость записи на диск в МБ/с
- `total_completed_tasks` - Общее количество выполненных задач
- `tasks_per_second` - Фактическая интенсивность нагрузки (задач/сек)

## Визуализация с Rich

При использовании библиотеки Rich будет отображена интерактивная панель со следующими элементами:
- Заголовок с общим статусом теста
- Таблица с текущими значениями метрик и их статусами
- Прогресс-бар для отображения шага прогрессии
- Сводная информация о времени работы и месте сохранения результатов

## Инструкция по запуску

1. Убедитесь, что все зависимости установлены:
   ```
   pip install boto3 redis sqlalchemy psutil celery rich
   ```

2. Поместите тестовое изображение `test.jpg` в корень проекта

3. Запустите скрипт из виртуального окружения:
   ```
   cd ~/facepass
   python stress_progression_v2.py
   ```

4. Для прерывания теста нажмите Ctrl+C

## Примечания по реализации

1. Использование тредов вместо процессов для симуляции точек нагрузки обеспечивает более легкое управление и мониторинг.

2. Асинхронная структура основного цикла позволяет эффективно управлять сбором метрик и отображением без блокирования.

3. Тайм-ауты и обработка ошибок во всех операциях повышают устойчивость скрипта к сбоям.

4. При отсутствии библиотеки Rich будет использован простой текстовый вывод в консоль.