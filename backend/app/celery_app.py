from __future__ import annotations
import os
from celery import Celery

celery = Celery(
    'tyakxa_backend',
    broker=os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'rpc://'),
)
celery.conf.timezone = os.getenv('TZ', 'America/Mexico_City')
celery.conf.task_serializer = 'json'
celery.conf.result_serializer = 'json'
celery.conf.accept_content = ['json']
