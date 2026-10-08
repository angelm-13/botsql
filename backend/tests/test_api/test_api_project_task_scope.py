from __future__ import annotations

from unittest.mock import patch

from app.models.entity_permission import EntityPermission
from app.models.field import Field
from app.models.nm_field_permission import NmFieldPermission
from app.models.proyect import Proyect
from app.models.session import transaction_context
from app.models.task import Task
from app.models.task_note import TaskNote
from tests.conftest import BackendTestCase
from tests.model_factory import build_model


class TestProjectTaskScopeApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.owner = {"id_user": 11, "id_permission": 101}
        self.other_owner = {"id_user": 12, "id_permission": 102}
        with transaction_context() as db:
            for permission_id, actor_id in ((101, 11), (102, 12)):
                db.add_all([
                    EntityPermission(id_permission=permission_id, entity_name="task", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=actor_id),
                    EntityPermission(id_permission=permission_id, entity_name="task_note", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=actor_id),
                ])
            # Permiso de CAMPO (no de entidad): sin esto, `_filter_payload_
            # for_actor` (routes/task_note.py) descarta `id_task`/
            # `task_note_description` del cuerpo antes de que lleguen al
            # servicio -ningun test anterior creaba una nota nueva via la
            # ruta generica, asi que este hueco de la fixture no se habia
            # topado antes.
            campo_id_task = build_model(Field, table_name="task_note", field_name="id_task", created_by=1)
            campo_descripcion = build_model(Field, table_name="task_note", field_name="task_note_description", created_by=1)
            db.add_all([campo_id_task, campo_descripcion])
            db.flush()
            for permission_id in (101, 102):
                for campo in (campo_id_task, campo_descripcion):
                    db.add(NmFieldPermission(
                        id_field=campo.id_field, id_permission=permission_id,
                        control_type="7", created_by=1))
            own_project = Proyect(
                id_customer_supplier=1,
                leader=11,
                proyect_description="Proyecto propio",
                title="Propio",
                proyect_status="draft",
                created_by=11,
            )
            foreign_project = Proyect(
                id_customer_supplier=1,
                leader=12,
                proyect_description="Proyecto ajeno",
                title="Ajeno",
                proyect_status="draft",
                created_by=12,
            )
            db.add_all([own_project, foreign_project])
            db.flush()
            own_task = build_model(Task, id_proyect=own_project.id_proyect, owner=11, created_by=11)
            foreign_task = build_model(Task, id_proyect=foreign_project.id_proyect, owner=12, created_by=12)
            db.add_all([own_task, foreign_task])
            db.flush()
            own_note = build_model(TaskNote, id_task=own_task.id_task, created_by=11)
            foreign_note = build_model(TaskNote, id_task=foreign_task.id_task, created_by=12)
            db.add_all([own_note, foreign_note])
            db.flush()
            self.own_task_id = own_task.id_task
            self.foreign_task_id = foreign_task.id_task
            self.own_note_id = own_note.id_task_note
            self.foreign_note_id = foreign_note.id_task_note

    def _request(self, actor, method, path, payload=None):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(
                path,
                method=method,
                json=payload,
                headers={"Authorization": "Bearer task-scope-test"},
            )

    def test_task_list_and_crud_are_owner_scoped(self):
        listing = self._request(self.owner, "GET", "/task/?page=1&per_page=20")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(self.json(listing)["total"], 1)
        self.assertEqual(self.json(listing)["items"][0]["id_task"], self.own_task_id)

        for method, payload in (("GET", None), ("PUT", {"title": "Intrusión"}), ("DELETE", None)):
            response = self._request(self.owner, method, f"/task/{self.foreign_task_id}", payload)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(self.json(response)["error_key"], "errors.resource_not_found")

    def test_task_note_list_and_crud_are_owner_scoped(self):
        listing = self._request(self.owner, "GET", "/task_note/?page=1&per_page=20")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(self.json(listing)["total"], 1)
        self.assertEqual(self.json(listing)["items"][0]["id_task_note"], self.own_note_id)

        for method, payload in (("GET", None), ("PUT", {"task_note_description": "Intrusión"}), ("DELETE", None)):
            response = self._request(self.owner, method, f"/task_note/{self.foreign_note_id}", payload)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(self.json(response)["error_key"], "errors.resource_not_found")

    def test_creating_a_task_note_through_the_generic_crud_requires_a_description(self):
        """Antes `POST /task_note/` llamaba a `TaskNoteService.create` directo
        -el CRUD generico, sin validar nada- y aceptaba una nota vacia.
        Hallazgo de la auditoria de seguridad del 2026-10-06."""
        response = self._request(self.owner, "POST", "/task_note/", {
            "id_task": self.own_task_id, "task_note_description": "   ",
        })
        self.assertEqual(400, response.status_code)
        self.assertEqual("errors.required_field", self.json(response)["error_key"])

    def test_creating_a_task_note_through_the_generic_crud_reaches_the_project_expediente(self):
        """La misma nota que antes solo vivia en `task_note` y nunca aparecia
        en `proyect_event` -el expediente del proyecto no se enteraba-.
        Hallazgo de la auditoria de seguridad del 2026-10-06."""
        from app.models.proyect_event import ProyectEvent
        from app.models.session import transaction_context as _tc

        response = self._request(self.owner, "POST", "/task_note/", {
            "id_task": self.own_task_id, "task_note_description": "Avance de hoy",
        })
        self.assertEqual(201, response.status_code)

        with _tc() as db:
            eventos = db.query(ProyectEvent).filter(
                ProyectEvent.id_task == self.own_task_id,
                ProyectEvent.event_type == "task_note",
            ).all()
            self.assertEqual(1, len(eventos))
            self.assertEqual("Avance de hoy", eventos[0].content)


if __name__ == "__main__":
    import unittest

    unittest.main()