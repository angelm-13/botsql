from __future__ import annotations

from app.models.entity_permission import EntityPermission
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.session import transaction_context
from app.services.project_management_service import (
    create_project,
    get_project_detail,
    list_projects,
    transition_project,
    update_project,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestProjectWorkflowService(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.supervisor = {"id_user": 11, "id_permission": 101}
        self.other_supervisor = {"id_user": 12, "id_permission": 102}
        self.manager = {"id_user": 21, "id_permission": 201}
        self.workshop = {"id_user": 31, "id_permission": 301}
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=201, entity_name="project_authorization", control_type=2, created_by=21),
                EntityPermission(id_permission=301, entity_name="project_execution", control_type=2, created_by=31),
            ])

    def _create(self, actor=None, title="Proyecto"):
        return create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo de fabricación",
            "title": title,
        }, actor or self.supervisor)

    def test_supervisor_creation_defaults_to_draft_and_is_owner_scoped(self):
        own = self._create()
        self._create(self.other_supervisor, "Ajeno")

        result = list_projects(self.supervisor)

        self.assertEqual(own["proyect_status"], "draft")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["created_by"], 11)

    def test_workshop_only_sees_authorized_or_operational_projects(self):
        project = self._create()
        self.assertEqual(list_projects(self.workshop)["total"], 0)

        transition_project(project["id_proyect"], {"status": "submitted"}, self.supervisor)
        self.assertEqual(list_projects(self.workshop)["total"], 0)

        transition_project(project["id_proyect"], {"status": "authorized"}, self.manager)
        self.assertEqual(list_projects(self.workshop)["total"], 1)

    def test_full_cycle_writes_ordered_immutable_history(self):
        project = self._create()
        project_id = project["id_proyect"]
        transition_project(project_id, {"status": "submitted"}, self.supervisor)
        transition_project(project_id, {"status": "authorized"}, self.manager)
        transition_project(project_id, {"status": "in_progress"}, self.workshop)
        transition_project(project_id, {"status": "stopped", "reason": "Falta material"}, self.workshop)
        transition_project(project_id, {"status": "in_progress"}, self.workshop)
        transition_project(project_id, {"status": "completed"}, self.workshop)

        detail = get_project_detail(project_id, self.workshop)

        self.assertEqual(detail["proyect_status"], "completed")
        self.assertEqual(len(detail["events"]), 7)
        self.assertEqual(detail["events"][0]["event_type"], "created")
        self.assertEqual(detail["events"][4]["reason"], "Falta material")
        with transaction_context() as db:
            self.assertEqual(db.query(ProyectEvent).filter_by(id_proyect=project_id).count(), 7)

    def test_direct_status_update_is_rejected(self):
        project = self._create()

        with self.assertRaises(AppError) as raised:
            update_project(project["id_proyect"], {"proyect_status": "completed"}, self.supervisor)

        self.assertEqual(raised.exception.message_key, "errors.project_status_requires_transition")
        with transaction_context() as db:
            stored = db.get(Proyect, project["id_proyect"])
            self.assertEqual(stored.proyect_status, "draft")

    def test_capability_cannot_execute_another_roles_transition(self):
        project = self._create()
        project_id = project["id_proyect"]
        transition_project(project_id, {"status": "submitted"}, self.supervisor)

        with self.assertRaises(AppError) as raised:
            transition_project(project_id, {"status": "authorized"}, self.workshop)

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    import unittest

    unittest.main()