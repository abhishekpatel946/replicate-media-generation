"""
Celery application configuration for background task processing.
Handles async job queue with Redis broker and result backend.
"""

from celery import Celery
from app.core.config import settings

# Create Celery application instance
celery_app = Celery(
    "fleek_media_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.media_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)
