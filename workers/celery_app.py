from celery import Celery
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fecapass",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
    include=['workers.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)
