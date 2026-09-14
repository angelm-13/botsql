from __future__ import annotations

from app.models.entity_permission import EntityPermission
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.session import transaction_context
from app.services.project_management_service import (
    create_project,
    delete_project,
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

class TestProjectLeaderRights(TestProjectWorkflowService):
    """El lider designado del proyecto.

    Antes el ambito propio se calculaba solo sobre `created_by`, de modo que un
    proyecto asignado a otra persona quedaba invisible para su propio
    responsable: no lo veia en su lista ni lo podia consultar, mucho menos
    moverlo. Un supervisor puede levantar el proyecto y asignarlo, y quien lo
    lidera es quien lo saca adelante.
    """

    def setUp(self):
        super().setUp()
        # Lucia lidera, pero no creo el proyecto ni tiene capacidades globales.
        self.leader = {"id_user": 41, "id_permission": 401}

    def _create_led_by_leader(self, title="Con lider"):
        return create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo asignado",
            "title": title,
            "leader": 41,
        }, self.supervisor)

    def test_the_leader_sees_the_project_they_did_not_create(self):
        self._create_led_by_leader()

        result = list_projects(self.leader)

        self.assertEqual(1, result["total"])
        self.assertEqual(11, result["items"][0]["created_by"])
        self.assertEqual(41, result["items"][0]["leader"])

    def test_the_leader_can_read_the_detail(self):
        project = self._create_led_by_leader()

        detail = get_project_detail(project["id_proyect"], self.leader)

        self.assertEqual(project["id_proyect"], detail["id_proyect"])

    def test_the_leader_submits_and_runs_their_project(self):
        project = self._create_led_by_leader()["id_proyect"]

        self.assertEqual(
            "submitted",
            transition_project(project, {"status": "submitted"}, self.leader)["proyect_status"],
        )
        transition_project(project, {"status": "authorized"}, self.manager)
        for target in ("in_progress", "completed"):
            with self.subTest(target=target):
                self.assertEqual(
                    target,
                    transition_project(project, {"status": target}, self.leader)["proyect_status"],
                )

    def test_the_leader_cannot_authorize_their_own_project(self):
        """Separacion de funciones: quien ejecuta el trabajo no lo aprueba.

        Es lo que evita que una sola persona levante, apruebe y cierre su
        propio proyecto.
        """
        project = self._create_led_by_leader()["id_proyect"]
        transition_project(project, {"status": "submitted"}, self.leader)

        for target in ("authorized", "denied", "blocked"):
            with self.subTest(target=target), self.assertRaises(AppError) as raised:
                transition_project(project, {"status": target, "reason": "Motivo"}, self.leader)
            self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_the_leader_can_stop_and_resume_with_a_reason(self):
        project = self._create_led_by_leader()["id_proyect"]
        transition_project(project, {"status": "submitted"}, self.leader)
        transition_project(project, {"status": "authorized"}, self.manager)
        transition_project(project, {"status": "in_progress"}, self.leader)

        with self.assertRaises(AppError):
            transition_project(project, {"status": "stopped"}, self.leader)

        stopped = transition_project(
            project, {"status": "stopped", "reason": "Falta material"}, self.leader
        )
        self.assertEqual("stopped", stopped["proyect_status"])

    def test_someone_who_is_neither_creator_nor_leader_sees_nothing(self):
        self._create_led_by_leader()
        forastero = {"id_user": 99, "id_permission": 999}

        self.assertEqual(0, list_projects(forastero)["total"])

    def test_the_leader_cannot_delete_a_project_someone_else_created(self):
        """El lider lo saca adelante, pero no lo elimina."""
        project = self._create_led_by_leader()["id_proyect"]

        with self.assertRaises(AppError) as raised:
            delete_project(project, self.leader)

        self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_the_creator_still_deletes_their_own_draft(self):
        project = self._create_led_by_leader()["id_proyect"]

        self.assertTrue(delete_project(project, self.supervisor)["deleted"])

    def test_the_leader_edits_their_project_while_it_is_editable(self):
        project = self._create_led_by_leader()["id_proyect"]

        updated = update_project(project, {"title": "Titulo del lider"}, self.leader)

        self.assertEqual("Titulo del lider", updated["title"])

    def test_the_workshop_sees_a_project_it_leads_before_authorization(self):
        """Un jefe de taller que ademas lidera no espera la autorizacion."""
        create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo propio del taller",
            "title": "Taller lider",
            "leader": 31,
        }, self.supervisor)

        self.assertEqual(1, list_projects(self.workshop)["total"])


class TestLaOrdenDeTrabajo(TestProjectWorkflowService):
    """Los atributos de la orden de trabajo (migracion 20260911180000)."""

    def test_the_work_order_fields_are_saved_and_returned(self):
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Mantenimiento de puerta",
            "title": "MEXINOX",
            "folio": "OT-2026-0042",
            "requested_by": "Francisco Molina",
            "purchase_order": "PO-MEXINOX-118",
            "purchase_order_item": 3,
            "delivery_date": "2026-10-15",
        }, self.supervisor)

        self.assertEqual("OT-2026-0042", creado["folio"])
        self.assertEqual("Francisco Molina", creado["requested_by"])
        self.assertEqual("PO-MEXINOX-118", creado["purchase_order"])
        self.assertEqual(3, creado["purchase_order_item"])
        self.assertEqual("2026-10-15", creado["delivery_date"])

    def test_a_real_folio_is_not_replaced_by_the_generated_one(self):
        """El folio propio no se pisa con el "PRJ-000006" autogenerado.

        `_project_payload` inventaba un folio SIEMPRE, sin mirar si el
        proyecto ya traia el suyo. El detalle -- no `create_project`, que
        devuelve el registro tal cual -- es donde se notaba: se veia bien al
        crearlo y cambiaba en cuanto alguien lo volvia a abrir.
        """
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Con folio propio",
            "folio": "OT-2026-0042",
        }, self.supervisor)

        detalle = get_project_detail(creado["id_proyect"], self.supervisor)

        self.assertEqual("OT-2026-0042", detalle["folio"])

    def test_a_project_without_a_folio_still_gets_the_generated_one(self):
        """El "PRJ-000006" sigue existiendo para quien no captura folio."""
        creado = self._create()

        detalle = get_project_detail(creado["id_proyect"], self.supervisor)

        self.assertEqual("PRJ-%06d" % creado["id_proyect"], detalle["folio"])

    def test_an_inexistent_quotation_is_rejected(self):
        with self.assertRaises(AppError) as fallo:
            create_project({
                "id_customer_supplier": 1,
                "proyect_description": "Con cotizacion inventada",
                "id_quotation": 999999,
            }, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)

    def test_an_inexistent_supervisor_is_rejected(self):
        with self.assertRaises(AppError) as fallo:
            create_project({
                "id_customer_supplier": 1,
                "proyect_description": "Con supervisor inventado",
                "id_supervisor": 999999,
            }, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)

    def test_updating_the_work_order_fields_validates_them_too(self):
        creado = self._create()

        with self.assertRaises(AppError) as fallo:
            update_project(creado["id_proyect"], {"id_supervisor": 999999}, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)
