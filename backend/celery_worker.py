
from app.jobs.celery_app import celery
from app.jobs.beat_schedule import BEAT_SCHEDULE

# Export as celery_app for CLI: celery -A celery_worker.celery
celery_app = celery

celery.conf.beat_schedule = BEAT_SCHEDULE

if __name__ == "__main__":
    celery.start()
