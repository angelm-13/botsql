from __future__ import annotations

from app.models.session import transaction_context
from app.services.notification_service import NotificationService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestNotificationService(BackendTestCase):
    def _create(self, id_user=11, notification_type="project_status_changed", title="Aviso"):
        with transaction_context() as db:
            notification = NotificationService.create_for_user(db, id_user, notification_type, title)
            db.flush()
            return notification.id_notification

    def test_unread_count_only_counts_this_users_unread(self):
        self._create(id_user=11)
        self._create(id_user=11)
        self._create(id_user=12)

        self.assertEqual(2, NotificationService.unread_count(11))
        self.assertEqual(1, NotificationService.unread_count(12))

    def test_mark_read_sets_read_at(self):
        id_notification = self._create(id_user=11)

        record = NotificationService.mark_read(id_notification, 11)

        self.assertIsNotNone(record["read_at"])
        self.assertEqual(0, NotificationService.unread_count(11))

    def test_mark_read_is_isolated_between_users(self):
        id_notification = self._create(id_user=11)

        with self.assertRaises(AppError) as raised:
            NotificationService.mark_read(id_notification, 12)
        self.assertEqual('errors.resource_not_found', raised.exception.message_key)
        self.assertEqual(1, NotificationService.unread_count(11))

    def test_mark_all_read_only_touches_that_user(self):
        self._create(id_user=11)
        self._create(id_user=11)
        self._create(id_user=12)

        NotificationService.mark_all_read(11)

        self.assertEqual(0, NotificationService.unread_count(11))
        self.assertEqual(1, NotificationService.unread_count(12))
