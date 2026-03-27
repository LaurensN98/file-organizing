import logging
from celery import Celery
from celery.signals import setup_logging
from app.core.config import settings


@setup_logging.connect
def config_loggers(*args, **kwargs):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Ensure our app logger is also at INFO
    logging.getLogger("app").setLevel(logging.INFO)


celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


# Autodiscover tasks in app directory
celery_app.autodiscover_tasks(["app"])
