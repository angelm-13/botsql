from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase


class TestProjectWorkflowApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.supervisor = {"id_user": 11, "id_permission": 101}
        self.other_supervisor = {"id_user": 12, "id_permission": 102}
        self.manager = {"id_user": 21, "id_permission": 201}
        self.workshop = {"id_user": 31, "id_permission": 301}
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=101, entity_name="proyect", scope_create=4, scope_read=4, scope_update=4, created_by=11),
                EntityPermission(id_permission=102, entity_name="proyect", scope_create=4, scope_read=4, scope_update=4, created_by=12),
                EntityPermission(id_permission=201, entity_name="proyect", scope_read=4, scope_update=4, created_by=21),
                EntityPermission(id_permission=201, entity_name="project_authorization", scope_read=4, created_by=21),
                EntityPermission(id_permission=301, entity_name="proyect", scope_read=4, scope_update=4, created_by=31),
                EntityPermission(id_permission=301, entity_name="project_execution", scope_read=4, created_by=31),
            ])

    def _request(self, actor, method, path, payload=None):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(
                path,
                method=method,
                json=payload,
                headers={"Authorization": "Bearer workflow-test"},
            )

    def _create_project(self):
        response = self._request(self.supervisor, "POST", "/proyect/", {
            "id_customer_supplier": 1,
            "leader": 999,
            "title": "Fabricación API",
            "proyect_description": "Proyecto creado desde la prueba HTTP",
            "proyect_status": "completed",
            "created_by": 999,
        })
        self.assertEqual(response.status_code, 201)
        return self.json(response)

    def test_role_workflow_and_history_through_http(self):
        project = self._create_project()
        project_id = project["id_proyect"]
        self.assertEqual(project["proyect_status"], "draft")
        self.assertEqual(project["created_by"], self.supervisor["id_user"])

        other_list = self._request(self.other_supervisor, "GET", "/proyect/?page=1&per_page=20")
        self.assertEqual(other_list.status_code, 200)
        self.assertEqual(self.json(other_list)["total"], 0)

        workshop_before = self._request(self.workshop, "GET", "/proyect/?page=1&per_page=20")
        self.assertEqual(self.json(workshop_before)["total"], 0)

        submitted = self._request(self.supervisor, "POST", f"/proyect/{project_id}/transition", {"status": "submitted"})
        self.assertEqual(submitted.status_code, 200)

        manager_list = self._request(self.manager, "GET", "/proyect/?page=1&per_page=20")
        manager_project = self.json(manager_list)["items"][0]
        self.assertEqual(manager_project["folio"], f"PRJ-{project_id:06d}")
        self.assertIsNotNone(manager_project["submitted_date"])

        tomorrow = (datetime.fromisoformat(manager_project["creation_date"]) + timedelta(days=1)).date().isoformat()
        future_list = self._request(
            self.manager,
            "GET",
            f"/proyect/?page=1&per_page=20&creation_date_from={tomorrow}",
        )
        self.assertEqual(self.json(future_list)["total"], 0)

        authorized = self._request(self.manager, "POST", f"/proyect/{project_id}/transition", {"status": "authorized"})
        self.assertEqual(authorized.status_code, 200)

        workshop_after = self._request(self.workshop, "GET", "/proyect/?page=1&per_page=20")
        self.assertEqual(self.json(workshop_after)["total"], 1)

        for status, reason in (
            ("in_progress", None),
            ("stopped", "Espera de material"),
            ("in_progress", None),
            ("completed", None),
        ):
            payload = {"status": status}
            if reason:
                payload["reason"] = reason
            response = self._request(self.workshop, "POST", f"/proyect/{project_id}/transition", payload)
            self.assertEqual(response.status_code, 200)

        detail = self._request(self.workshop, "GET", f"/proyect/{project_id}")
        detail_payload = self.json(detail)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail_payload["proyect_status"], "completed")
        self.assertEqual(len(detail_payload["events"]), 7)
        self.assertEqual(detail_payload["events"][4]["reason"], "Espera de material")

    def test_http_rejects_manual_status_and_wrong_role_transition(self):
        project = self._create_project()
        project_id = project["id_proyect"]

        bypass = self._request(self.supervisor, "PUT", f"/proyect/{project_id}", {"proyect_status": "completed"})
        self.assertEqual(bypass.status_code, 409)
        self.assertEqual(self.json(bypass)["error_key"], "errors.project_status_requires_transition")

        self._request(self.supervisor, "POST", f"/proyect/{project_id}/transition", {"status": "submitted"})
        wrong_role = self._request(self.workshop, "POST", f"/proyect/{project_id}/transition", {"status": "authorized"})
        self.assertEqual(wrong_role.status_code, 404)
        self.assertEqual(self.json(wrong_role)["error_key"], "errors.resource_not_found")

    def test_http_requires_reason_for_blocking(self):
        project = self._create_project()
        project_id = project["id_proyect"]
        self._request(self.supervisor, "POST", f"/proyect/{project_id}/transition", {"status": "submitted"})

        response = self._request(self.manager, "POST", f"/proyect/{project_id}/transition", {"status": "blocked"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.json(response)["error_key"], "errors.project_transition_reason_required")


if __name__ == "__main__":
    import unittest

    unittest.main()