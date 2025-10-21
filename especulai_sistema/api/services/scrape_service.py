"""
Serviço para acionar scraping via Celery ou fallback local.
"""

import os
from celery import Celery


def get_celery() -> Celery:
    celery = Celery(__name__)
    celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    return celery


def start_scrapy_task():
    """Dispara a task de scraping se Celery estiver configurado."""
    celery = get_celery()
    task = celery.send_task("start_scrapy_spider")
    return {"message": "Scraping iniciado em segundo plano", "task_id": task.id}


