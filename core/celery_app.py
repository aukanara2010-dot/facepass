"""
Celery application configuration for FacePass.

Handles asynchronous task processing (e.g., face indexing) using Redis as broker.
Results are intentionally ignored — only side effects (DB writes) matter.
"""

import multiprocessing
import os

from celery import Celery

# ---------------------------------------------------------------------------
# Broker / backend — read credentials from environment / .env
# ---------------------------------------------------------------------------
_redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
_redis_port = os.getenv("REDIS_PORT", "6379")
_redis_db   = os.getenv("REDIS_DB", "0")
_redis_pass = os.getenv("REDIS_PASSWORD", "")

if _redis_pass:
    REDIS_URL = f"redis://:{_redis_pass}@{_redis_host}:{_redis_port}/{_redis_db}"
else:
    REDIS_URL = f"redis://{_redis_host}:{_redis_port}/{_redis_db}"

# ---------------------------------------------------------------------------
# Worker concurrency: use half the available cores, capped at 4,
# so the CPU stays available for real-time face-search requests.
# ---------------------------------------------------------------------------
_cpu_count = multiprocessing.cpu_count()
_concurrency = min(4, max(2, _cpu_count // 2))

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
celery_app = Celery(
    "facepass",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.tasks"],
)

celery_app.conf.update(
    # We only care about the side-effect (writing to DB), not the return value.
    task_ignore_result=True,

    # Limit parallelism so indexing doesn't starve the search workers.
    worker_concurrency=_concurrency,

    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Retry policy for the broker connection on startup
    broker_connection_retry_on_startup=True,
)
