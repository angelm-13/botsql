from __future__ import annotations

from datetime import date, timedelta

from app.jobs.tasks_notifications import check_missing_activity_logs
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.user import User
from app.services.notification_service import NotificationService
from tests.conftest import BackendTestCase


def _last_business_day(today):
    anterior = today - timedelta(days=1)
    while anterior.weekday() >= 5:
        anterior -= timedelta(days=1)
    return anterior


class TestCheckMissingActivityLogs(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                Permission(id_permission=2, permission_description="Supervisor", authorized_by=1,
                           id_department=1, id_subdepartment=1, id_level=1, created_by=1),
                Permission(id_permission=3, permission_description="Gerente", authorized_by=1,
                           id_department=1, id_subdepartment=1, id_level=1, created_by=1),
            ])
            db.flush()
            db.add_all([
                User(id_user=11, full_name="Con bitacora", username="con_bitacora",
                     id_permission=2, id_proyect=1, id_status=1, supervisor=1, created_by=1),
                User(id_user=12, full_name="Sin bitacora", username="sin_bitacora",
                     id_permission=2, id_proyect=1, id_status=1, supervisor=1, created_by=1),
                User(id_user=21, full_name="Gerente", username="gerente",
                     id_permission=3, id_proyect=1, id_status=1, supervisor=1, created_by=1),
            ])
            db.flush()

    def test_notifies_only_the_supervisor_who_did_not_log_the_last_business_day(self):
        target = _last_business_day(date.today())
        with transaction_context() as db:
            db.add(SupervisorActivityLog(
                id_user=11, activity_date=target, content="Reviso avance de piso",
                created_by=11,
            ))

        check_missing_activity_logs.run()

        self.assertEqual(0, NotificationService.unread_count(11))
        self.assertEqual(1, NotificationService.unread_count(12))
        # Gerente no lleva bitacora -- no es Supervisor -- asi que no se le
        # reclama nada.
        self.assertEqual(0, NotificationService.unread_count(21))

    def test_running_it_twice_does_not_duplicate_the_reminder(self):
        check_missing_activity_logs.run()
        check_missing_activity_logs.run()

        self.assertEqual(1, NotificationService.unread_count(12))
