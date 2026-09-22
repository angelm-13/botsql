from __future__ import annotations

from app.models.customer_contact import CustomerContact
from app.models.entity_permission import EntityPermission
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.session import transaction_context
from app.services.project_management_service import (
    add_project_payment,
    create_project,
    delete_project,
    delete_project_payment,
    get_project_detail,
    list_projects,
    settle_project_payment,
    transition_management,
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
                EntityPermission(id_permission=201, entity_name="project_authorization", scope_read=4, created_by=21),
                EntityPermission(id_permission=301, entity_name="project_execution", scope_read=4, created_by=31),
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

        transition_project(project["id_proyect"], {"status": "authorized"}, self.manager)
        self.assertEqual(list_projects(self.workshop)["total"], 1)

    def test_full_cycle_writes_ordered_immutable_history(self):
        # Gerente mueve el proyecto directo desde Borrador -- al recibir la
        # orden de compra -- sin que Supervisor lo "envie a revision" primero.
        project = self._create()
        project_id = project["id_proyect"]
        transition_project(project_id, {"status": "authorized"}, self.manager)
        transition_project(project_id, {"status": "in_progress"}, self.workshop)
        transition_project(project_id, {"status": "stopped", "reason": "Falta material"}, self.workshop)
        transition_project(project_id, {"status": "in_progress"}, self.workshop)
        transition_project(project_id, {"status": "completed"}, self.workshop)

        detail = get_project_detail(project_id, self.workshop)

        self.assertEqual(detail["proyect_status"], "completed")
        self.assertEqual(len(detail["events"]), 6)
        self.assertEqual(detail["events"][0]["event_type"], "created")
        self.assertEqual(detail["events"][3]["reason"], "Falta material")
        with transaction_context() as db:
            self.assertEqual(db.query(ProyectEvent).filter_by(id_proyect=project_id).count(), 6)

    def test_direct_status_update_is_rejected(self):
        project = self._create()

        with self.assertRaises(AppError) as raised:
            update_project(project["id_proyect"], {"proyect_status": "completed"}, self.supervisor)

        self.assertEqual(raised.exception.message_key, "errors.project_status_requires_transition")
        with transaction_context() as db:
            stored = db.get(Proyect, project["id_proyect"])
            self.assertEqual(stored.proyect_status, "draft")

    def test_supervisor_can_no_longer_move_a_draft_out_of_draft(self):
        """Solo Gerente saca un proyecto de Borrador -- al recibir la orden
        de compra es cuando cambia el estatus, no Supervisor. Ni siquiera
        hacia "submitted", el paso que antes usaba para "enviarlo a revision".
        """
        project = self._create()["id_proyect"]

        for destino in ("submitted", "authorized", "denied", "blocked"):
            with self.subTest(destino=destino), self.assertRaises(AppError) as raised:
                transition_project(project, {"status": destino, "reason": "Motivo"}, self.supervisor)
            self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_manager_authorizes_a_draft_directly_without_a_submit_step(self):
        """Gerente mueve el proyecto directo desde Borrador -> Autorizado."""
        project = self._create()["id_proyect"]

        autorizado = transition_project(project, {"status": "authorized"}, self.manager)

        self.assertEqual("authorized", autorizado["proyect_status"])

    def test_capability_cannot_execute_another_roles_transition(self):
        project = self._create()
        project_id = project["id_proyect"]

        with self.assertRaises(AppError) as raised:
            transition_project(project_id, {"status": "authorized"}, self.workshop)

        self.assertEqual(raised.exception.status_code, 404)

    def test_workshop_can_block_a_project_already_in_progress(self):
        """Jefe de taller bloquea un proyecto que ya esta en curso.

        Distinto de rechazarlo ANTES de iniciar (desde Borrador), que sigue
        siendo exclusivo de Gerente.
        """
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        transition_project(project, {"status": "in_progress"}, self.workshop)

        blocked = transition_project(
            project, {"status": "blocked", "reason": "Falta permiso"}, self.workshop,
        )
        self.assertEqual("blocked", blocked["proyect_status"])

    def test_workshop_cannot_block_a_project_before_it_starts(self):
        """Rechazar antes de iniciar sigue siendo exclusivo de Gerente.

        Un proyecto en Borrador ni siquiera es VISIBLE para el taller
        todavia (no esta en WORKSHOP_VISIBLE_STATUSES y el taller no lo
        lidera), asi que el rechazo llega como 404 -no ve el proyecto- antes
        de que el candado de permiso de la transicion entre en juego.
        """
        project = self._create()["id_proyect"]

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "blocked", "reason": "Motivo"}, self.workshop)
        self.assertEqual("errors.resource_not_found", raised.exception.message_key)

    def test_management_transition_is_exclusive_to_the_manager(self):
        """Autorizar/cancelar el recorrido comercial es exclusivo de Gerente.

        Antes cualquier actor con `proyect:update` y visibilidad del proyecto
        -incluido el propio Supervisor sobre su proyecto- podia moverlo.
        """
        project = self._create()["id_proyect"]

        with self.assertRaises(AppError) as raised:
            transition_management(project, {"management_status": "autorizado"}, self.supervisor)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        autorizado = transition_management(
            project, {"management_status": "autorizado"}, self.manager,
        )
        self.assertEqual("autorizado", autorizado["management_status"])

    def test_payments_are_exclusive_to_the_manager(self):
        """Las parcialidades cuelgan del mismo recorrido comercial que
        `transition_management` y comparten su candado: Supervisor las ve
        (via `get_project_detail`) pero no puede acordarlas, cobrarlas ni
        quitarlas, aunque sea el lider del proyecto y tenga `proyect:update`.
        """
        project = self._create()["id_proyect"]

        with self.assertRaises(AppError) as raised:
            add_project_payment(
                project, {"payment_date": "2026-09-22", "amount": "100"}, self.supervisor,
            )
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        pago = add_project_payment(
            project, {"payment_date": "2026-09-22", "amount": "100"}, self.manager,
        )

        with self.assertRaises(AppError) as raised:
            settle_project_payment(
                pago["id_proyect_payment"], {"paid_at": "2026-09-23"}, self.supervisor,
            )
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        with self.assertRaises(AppError) as raised:
            delete_project_payment(pago["id_proyect_payment"], self.supervisor)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        cobrado = settle_project_payment(
            pago["id_proyect_payment"], {"paid_at": "2026-09-23"}, self.manager,
        )
        self.assertEqual("2026-09-23", cobrado["paid_at"])

        borrado = delete_project_payment(pago["id_proyect_payment"], self.manager)
        self.assertEqual(pago["id_proyect_payment"], borrado["id_proyect_payment"])

    def test_the_leader_is_always_the_creator_regardless_of_payload(self):
        """El responsable es siempre quien crea, sin excepcion de rol.

        Antes un supervisor podia levantar un proyecto y asignarlo a otro
        responsable (delegacion). Decision de negocio: ya no -- ni al crear
        ni al editar despues, sin importar lo que venga en el payload.
        """
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo de fabricación",
            "leader": 999,
        }, self.supervisor)
        self.assertEqual(self.supervisor["id_user"], creado["leader"])

        actualizado = update_project(creado["id_proyect"], {"leader": 999}, self.supervisor)
        self.assertEqual(self.supervisor["id_user"], actualizado["leader"])


if __name__ == "__main__":
    import unittest

    unittest.main()


class TestLaOrdenDeTrabajo(TestProjectWorkflowService):
    """Los atributos de la orden de trabajo (migracion 20260911180000)."""

    def test_the_work_order_fields_are_saved_and_returned(self):
        with transaction_context() as db:
            contacto = CustomerContact(
                id_customer_supplier=1, full_name="Francisco Molina", created_by=11,
            )
            db.add(contacto)
            db.flush()
            id_contacto = contacto.id_customer_contact

        creado = create_project({
            "id_customer_supplier": 1,
            "id_customer_contact": id_contacto,
            "proyect_description": "Mantenimiento de puerta",
            "title": "MEXINOX",
            "folio": "OT-2026-0042",
            "purchase_order": "PO-MEXINOX-118",
            "purchase_order_item": 3,
            "delivery_date": "2026-10-15",
        }, self.supervisor)

        self.assertEqual("OT-2026-0042", creado["folio"])
        self.assertEqual(id_contacto, creado["id_customer_contact"])
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

    def test_an_inexistent_customer_contact_is_rejected(self):
        with self.assertRaises(AppError) as fallo:
            create_project({
                "id_customer_supplier": 1,
                "proyect_description": "Con contacto inventado",
                "id_customer_contact": 999999,
            }, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)

    def test_updating_the_work_order_fields_validates_them_too(self):
        creado = self._create()

        with self.assertRaises(AppError) as fallo:
            update_project(creado["id_proyect"], {"id_customer_contact": 999999}, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)
