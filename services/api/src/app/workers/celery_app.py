import os
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "krishinet_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min hard limit
    beat_schedule={
        "periodic-outbreak-refresh-hourly": {
            "task": "app.workers.tasks.refresh_outbreak_clusters",
            "schedule": 3600.0,  # every hour
        },
        "daily-field-intelligence-refresh": {
            "task": "app.workers.tasks.refresh_all_active_fields",
            "schedule": 86400.0,  # every 24 hours (satellite + soil + weather)
        },
        "six-hour-weather-refresh": {
            "task": "app.workers.tasks.refresh_weather_active_fields",
            "schedule": 21600.0,  # every 6 hours (weather forecasts & hazards)
        },
    },
)
