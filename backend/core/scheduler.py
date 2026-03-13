from celery import Celery
from celery.schedules import crontab

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "crawtopia",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "check-election-cycle": {
        "task": "backend.core.tasks.check_election_cycle",
        "schedule": 15.0,  # every 15 seconds
    },
    "mark-stale-agents": {
        "task": "backend.core.tasks.mark_stale_agents",
        "schedule": 300.0,  # every 5 minutes
    },
    "check-founding-conditions": {
        "task": "backend.core.tasks.check_founding_conditions",
        "schedule": 30.0,  # every 30 seconds during bootstrap
    },
}
