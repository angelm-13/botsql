
from __future__ import annotations

from celery.schedules import crontab


BEAT_SCHEDULE = {
    "recalculate-kpi-snapshots-nightly": {
        "task": "app.jobs.tasks_kpis.recalculate_kpi_snapshots",
        "schedule": crontab(hour=1, minute=0),
    },
    "audit-entities-nightly": {
        "task": "app.jobs.tasks_entity.run_all_entity_audits",
        "schedule": crontab(hour=2, minute=0),
    },
    "recalculate-inventory-hourly": {
        "task": "app.jobs.tasks_scm.recalculate_inventory",
        "schedule": crontab(minute=0),
    },
    "detect-stock-risk-hourly": {
        "task": "app.jobs.tasks_scm.detect_stock_risk",
        "schedule": crontab(minute=15),
    },
    "sync-crm-segments-daily": {
        "task": "app.jobs.tasks_crm.sync_customer_segments",
        "schedule": crontab(hour=3, minute=30),
    },
    "maintenance-cleanup-daily": {
        "task": "app.jobs.tasks_maintenance.cleanup_expired_results",
        "schedule": crontab(hour=4, minute=0),
    },
    "appointment-notifications-every-five-minutes": {
        "task": "app.jobs.tasks_appointments.dispatch_due_notifications",
        "schedule": crontab(minute="*/5"),
    },
}
