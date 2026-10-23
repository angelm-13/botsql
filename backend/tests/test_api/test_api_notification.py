from __future__ import annotations

import jwt

from app.models.session import transaction_context
from app.services.notification_service import NotificationService
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestNotificationApi(BackendTestCase):
    def _token(self, id_user):
        return jwt.encode({"id_user": id_user, "is_bootstrap_admin": True}, SECRET_KEY, algorithm="HS256")

    def _headers(self, id_user):
        return {"Authorization": f"Bearer {self._token(id_user)}"}

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            NotificationService.create_for_user(db, 11, "project_status_changed", "Para el 11")
            NotificationService.create_for_user(db, 12, "project_status_changed", "Para el 12")

    def test_a_user_only_lists_their_own_notifications(self):
        response = self.client.get("/notification/", headers=self._headers(11))

        payload = self.json(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, payload["total"])
        self.assertEqual("Para el 11", payload["items"][0]["title"])

    def test_unread_count_is_isolated(self):
        response_11 = self.client.get("/notification/unread-count", headers=self._headers(11))
        response_12 = self.client.get("/notification/unread-count", headers=self._headers(12))

        self.assertEqual(1, self.json(response_11)["unread_count"])
        self.assertEqual(1, self.json(response_12)["unread_count"])

    def test_marking_one_user_notification_read_does_not_affect_the_other(self):
        listado = self.json(self.client.get("/notification/", headers=self._headers(11)))
        id_notification = listado["items"][0]["id_notification"]

        response = self.client.patch(f"/notification/{id_notification}/read", headers=self._headers(11))
        self.assertEqual(200, response.status_code)

        self.assertEqual(0, self.json(self.client.get("/notification/unread-count", headers=self._headers(11)))["unread_count"])
        self.assertEqual(1, self.json(self.client.get("/notification/unread-count", headers=self._headers(12)))["unread_count"])

    def test_a_user_cannot_mark_someone_elses_notification_as_read(self):
        listado = self.json(self.client.get("/notification/", headers=self._headers(11)))
        id_notification = listado["items"][0]["id_notification"]

        response = self.client.patch(f"/notification/{id_notification}/read", headers=self._headers(12))

        self.assertEqual(404, response.status_code)
