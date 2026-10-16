from __future__ import annotations

from datetime import datetime

from app.models.customer_contact import CustomerContact
from app.models.entity_permission import EntityPermission
from app.models.invoice import Invoice
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.session import transaction_context
from app.models.task import Task
from app.services.project_management_service import (
    add_project_payment,
    create_project,
    delete_project,
    delete_project_payment,
    get_project_detail,
    list_projects,
    release_project,
    settle_project_payment,
    take_project,
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
                # Borrar lo manda `scope_delete` de `proyect` (Gestor): Propios
                # para quien levanta/ejecuta, Todos para Gerente.
                EntityPermission(id_permission=101, entity_name="proyect", scope_delete=1, created_by=11),
                EntityPermission(id_permission=201, entity_name="proyect", scope_delete=4, created_by=21),
                EntityPermission(id_permission=301, entity_name="proyect", scope_delete=1, created_by=31),
                EntityPermission(id_permission=401, entity_name="proyect", scope_delete=1, created_by=41),
            ])

    def _create(self, actor=None, title="Proyecto"):
        return create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo de fabricación",
            "title": title,
        }, actor or self.supervisor)

    def _add_task(self, project_id, task_status="pendiente"):
        with transaction_context() as db:
            db.add(Task(
                id_proyect=project_id, task_description="Tarea", task_status=task_status,
                owner=self.workshop["id_user"], validation=self.workshop["id_user"], dependency=0,
                created_by=self.workshop["id_user"],
            ))

    def _start_work(self, project_id):
        """De `authorized` a `in_progress` pasando por la espera de material
        obligatoria -- ambos saltos los pide Gerente, no el taller (ver el
        comentario de PROJECT_STATUSES en project_management_service.py)."""
        transition_project(project_id, {"status": "waiting_material"}, self.manager)
        return transition_project(project_id, {"status": "in_progress"}, self.manager)

    def test_supervisor_creation_defaults_to_draft_and_is_owner_scoped(self):
        own = self._create()
        self._create(self.other_supervisor, "Ajeno")

        result = list_projects(self.supervisor)

        self.assertEqual(own["proyect_status"], "draft")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["created_by"], 11)

    def test_the_listing_says_how_many_pages_there_are(self):
        """Sin `pages` la pantalla asume una sola y deshabilita Siguiente."""
        for nombre in ("Uno", "Dos", "Tres"):
            self._create(self.supervisor, nombre)

        result = list_projects(self.supervisor, per_page=2)

        self.assertEqual(3, result["total"])
        self.assertEqual(2, result["pages"])

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
        self._add_task(project_id, "terminada")
        self._start_work(project_id)
        transition_project(project_id, {"status": "stopped", "reason": "Falta material"}, self.workshop)
        transition_project(project_id, {"status": "in_progress"}, self.workshop)
        transition_project(project_id, {"status": "completed"}, self.workshop)

        detail = get_project_detail(project_id, self.workshop)

        self.assertEqual(detail["proyect_status"], "completed")
        # created, authorized, waiting_material, in_progress, stopped,
        # in_progress, completed -- un evento mas que antes de que la espera
        # de material fuera obligatoria.
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

    def test_an_authorized_project_cannot_skip_the_wait_for_material(self):
        """Ya no hay salida directa de `authorized` a `in_progress` -- una
        orden de compra puede surtir a varios proyectos a la vez (ej. los
        mismos costales de cemento), asi que autorizar no significa que el
        taller ya tenga en mano lo que necesita. Debe pasar por
        `waiting_material`, sin importar quien lo pida.
        """
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project)

        for actor in (self.manager, self.workshop):
            with self.subTest(actor=actor), self.assertRaises(AppError) as raised:
                transition_project(project, {"status": "in_progress"}, actor)
            self.assertEqual("errors.project_invalid_transition", raised.exception.message_key)

    def test_only_the_manager_opens_and_closes_the_wait_for_material(self):
        """Entrar a la espera y salir de ella hacia el trabajo real las
        decide quien autoriza/compra (Gerente), no el taller -- es quien
        sabe si la compra ya llego. El taller SI puede pausar un proyecto ya
        en curso por falta de material (`in_progress -> waiting_material`,
        cubierto en `test_full_cycle_writes_ordered_immutable_history`), pero
        no controla la espera de arranque.
        """
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project)

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "waiting_material"}, self.workshop)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        en_espera = transition_project(project, {"status": "waiting_material"}, self.manager)
        self.assertEqual("waiting_material", en_espera["proyect_status"])

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "in_progress"}, self.workshop)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        en_proceso = transition_project(project, {"status": "in_progress"}, self.manager)
        self.assertEqual("in_progress", en_proceso["proyect_status"])

    def test_capability_cannot_execute_another_roles_transition(self):
        project = self._create()
        project_id = project["id_proyect"]

        with self.assertRaises(AppError) as raised:
            transition_project(project_id, {"status": "authorized"}, self.workshop)

        self.assertEqual(raised.exception.status_code, 404)

    def test_workshop_cannot_block_a_project_already_in_progress(self):
        """Jefe de taller NO bloquea un proyecto en curso -- lo suyo es
        "detenido" (`stopped`). Bloquear un proyecto en curso queda para
        quien lo lidera (o quien autoriza).
        """
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project)
        self._start_work(project)

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "blocked", "reason": "Falta permiso"}, self.workshop)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        detenido = transition_project(project, {"status": "stopped", "reason": "Falta material"}, self.workshop)
        self.assertEqual("stopped", detenido["proyect_status"])

    def test_leader_can_block_a_project_already_in_progress(self):
        """Quien lidera el proyecto si puede bloquearlo en curso, aunque no
        tenga la capacidad de autorizacion ni sea del taller."""
        project = self._create()["id_proyect"]  # self.supervisor es el lider por defecto.
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project)
        self._start_work(project)

        blocked = transition_project(
            project, {"status": "blocked", "reason": "Falta permiso"}, self.supervisor,
        )
        self.assertEqual("blocked", blocked["proyect_status"])

    def test_project_cannot_move_to_in_progress_without_tasks(self):
        """No se arranca un proyecto que todavia no tiene tareas.

        El candado vive en la salida real hacia el trabajo
        (`waiting_material -> in_progress`), no al entrar a la espera de
        material -- las tareas se van definiendo mientras el material esta
        en camino, no antes.
        """
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        transition_project(project, {"status": "waiting_material"}, self.manager)

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "in_progress"}, self.manager)
        self.assertEqual("errors.project_requires_task", raised.exception.message_key)

        self._add_task(project)
        en_proceso = transition_project(project, {"status": "in_progress"}, self.manager)
        self.assertEqual("in_progress", en_proceso["proyect_status"])

    def test_a_blank_description_is_not_a_description(self):
        with self.assertRaises(AppError) as e:
            create_project({"id_customer_supplier": 1, "proyect_description": "   ",
                            "title": "T"}, self.supervisor)
        self.assertEqual(400, e.exception.status_code)

    def test_project_with_unreceived_material_needs_a_reason_to_start(self):
        """Arrancar con material por recibir exige motivo de quien autoriza."""
        from app.models.proyect_material_need import ProyectMaterialNeed

        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project)
        with transaction_context() as db:
            db.add(ProyectMaterialNeed(
                id_proyect=project, description="Lamina", quantity=5, created_by=11))
        transition_project(project, {"status": "waiting_material"}, self.manager)

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "in_progress"}, self.manager)
        self.assertEqual("errors.project_material_pending", raised.exception.message_key)
        self.assertEqual(1, get_project_detail(project, self.manager)["material_readiness"]["not_ordered"])

        en_proceso = transition_project(
            project, {"status": "in_progress", "reason": "Llega el lunes"}, self.manager)
        self.assertEqual("in_progress", en_proceso["proyect_status"])

    def test_project_cannot_be_completed_with_open_tasks(self):
        """No se completa el proyecto si todavia hay tareas sin cerrar."""
        project = self._create()["id_proyect"]
        transition_project(project, {"status": "authorized"}, self.manager)
        self._add_task(project, "pendiente")
        self._start_work(project)

        with self.assertRaises(AppError) as raised:
            transition_project(project, {"status": "completed"}, self.workshop)
        self.assertEqual("errors.project_tasks_not_completed", raised.exception.message_key)

        with transaction_context() as db:
            db.query(Task).filter(Task.id_proyect == project).update({"task_status": "terminada"})

        completado = transition_project(project, {"status": "completed"}, self.workshop)
        self.assertEqual("completed", completado["proyect_status"])

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
        """Un proyecto cuyo responsable NO es quien lo creo.

        Ya no se puede pedir al crearlo -- `create_project` pone siempre al
        actor y descarta el `leader` del cuerpo --, pero la situacion sigue
        existiendo en datos reales: todos los proyectos levantados antes de ese
        cambio pudieron asignarse a otra persona desde el formulario. Se
        reproduce escribiendo la columna, que es exactamente como esos
        proyectos estan hoy en la base, y lo que se prueba sigue vivo: que el
        ambito propio mire `leader` y no solo `created_by`.
        """
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo asignado",
            "title": title,
        }, self.supervisor)
        with transaction_context() as db:
            db.get(Proyect, creado["id_proyect"]).leader = 41
        creado["leader"] = 41
        return creado

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
        """Gerente autoriza directo desde Borrador; el lider ejecuta despues.

        Entre "autorizado" y "en proceso" va la espera de material
        obligatoria (`waiting_material`), y esa la controla quien autoriza
        -- no el lider -- porque es quien sabe si la compra ya llego.
        """
        project = self._create_led_by_leader()["id_proyect"]
        self._add_task(project, "terminada")

        transition_project(project, {"status": "authorized"}, self.manager)
        self._start_work(project)

        self.assertEqual(
            "completed",
            transition_project(project, {"status": "completed"}, self.leader)["proyect_status"],
        )

    def test_the_leader_cannot_authorize_their_own_project(self):
        """Separacion de funciones: quien ejecuta el trabajo no lo aprueba.

        Es lo que evita que una sola persona levante, apruebe y cierre su
        propio proyecto.
        """
        project = self._create_led_by_leader()["id_proyect"]

        for target in ("authorized", "denied", "blocked"):
            with self.subTest(target=target), self.assertRaises(AppError) as raised:
                transition_project(project, {"status": target, "reason": "Motivo"}, self.leader)
            self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_the_leader_can_stop_and_resume_with_a_reason(self):
        project = self._create_led_by_leader()["id_proyect"]
        self._add_task(project)
        transition_project(project, {"status": "authorized"}, self.manager)
        self._start_work(project)

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

    def test_who_can_delete_is_decided_by_the_role_manager_scope(self):
        """Todos borra el de cualquiera; Propios solo el que el actor creo; sin permiso, nada."""
        del_supervisor = self._create(self.supervisor, "Del supervisor")["id_proyect"]
        del_gerente = self._create(self.manager, "Del gerente")["id_proyect"]
        del_taller = self._create(self.workshop, "Del taller")["id_proyect"]

        # Propios: el jefe de taller no borra el del supervisor.
        with self.assertRaises(AppError):
            delete_project(del_supervisor, self.workshop)
        self.assertTrue(delete_project(del_taller, self.workshop)["deleted"])
        # Todos: el gerente borra el que levanto otro.
        self.assertTrue(delete_project(del_supervisor, self.manager)["deleted"])
        self.assertTrue(delete_project(del_gerente, self.manager)["deleted"])

    def test_without_delete_permission_nobody_deletes_even_their_own(self):
        project = self._create(self.supervisor)["id_proyect"]
        with transaction_context() as db:
            db.query(EntityPermission).filter_by(
                id_permission=101, entity_name="proyect").update({"scope_delete": 0})

        with self.assertRaises(AppError) as raised:
            delete_project(project, self.supervisor)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_the_leader_edits_their_project_while_it_is_editable(self):
        project = self._create_led_by_leader()["id_proyect"]

        updated = update_project(project, {"title": "Titulo del lider"}, self.leader)

        self.assertEqual("Titulo del lider", updated["title"])

    def test_the_workshop_sees_a_project_it_leads_before_authorization(self):
        """Un jefe de taller que ademas lidera no espera la autorizacion."""
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo propio del taller",
            "title": "Taller lider",
        }, self.supervisor)
        # Igual que en `_create_led_by_leader`: el responsable ya no se elige al
        # crear, pero los proyectos que ya lo tienen distinto siguen ahi.
        with transaction_context() as db:
            db.get(Proyect, creado["id_proyect"]).leader = 31

        self.assertEqual(1, list_projects(self.workshop)["total"])

    def test_who_can_create_is_decided_by_the_role_manager_not_the_scope(self):
        """Gerente y Jefe de taller crean si el Gestor se lo concedio.

        La ruta ya exige `scope_create` de `proyect`; el servicio no pone un
        segundo candado por ambito. El creador queda como responsable y ve su
        propio proyecto.
        """
        del_gerente = self._create(self.manager, "Del gerente")
        del_taller = self._create(self.workshop, "Del taller")

        self.assertEqual(self.manager["id_user"], del_gerente["leader"])
        self.assertEqual(self.workshop["id_user"], del_taller["leader"])
        self.assertEqual("draft", del_taller["proyect_status"])
        self.assertEqual(2, list_projects(self.manager)["total"])
        self.assertEqual(1, list_projects(self.workshop)["total"])


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
        """El folio propio no se pisa con el generado automaticamente.

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
        """El folio "PRJ-000006" sigue existiendo para quien no captura folio."""
        creado = self._create()

        detalle = get_project_detail(creado["id_proyect"], self.supervisor)

        self.assertEqual("PRJ-%06d" % creado["id_proyect"], detalle["folio"])

    def _invoice(self, id_invoice):
        """Un `invoice` minimo, real, para las pruebas de cotizacion.

        SQLite (donde corre la suite) no impone las FK de `id_customer_supplier`/
        `id_status` -igual que el resto de fixtures de este archivo, que usan
        `id_customer_supplier: 1` sin crearlo-, asi que basta con satisfacer los
        NOT NULL de la tabla.
        """
        with transaction_context() as db:
            db.add(Invoice(
                id_invoice=id_invoice, id_customer_supplier=1, id_issuer_customer_supplier=1,
                tax_certification_supplier=1, id_status=1, created_by=1,
                apply_tax=False, tax_rate=0,
            ))

    def test_a_quotation_with_no_matching_invoice_is_kept_as_external_reference(self):
        """Un folio de un sistema externo (ej. adser) se acepta tal cual.

        Antes cualquier numero que no fuera un `invoice` real tronaba con
        `errors.not_found` -- rompia el caso de un cliente que cotiza fuera de
        tyakxa_tny y solo pega ese folio como referencia.
        """
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Con folio externo",
            "id_quotation": "COT-2026-045",
        }, self.supervisor)

        self.assertIsNone(creado["id_quotation"])
        self.assertEqual("COT-2026-045", creado["quotation_reference"])

    def test_a_quotation_matching_a_free_invoice_is_linked(self):
        """Un `id_quotation` real que ningun proyecto usa todavia se liga de verdad."""
        self._invoice(500)

        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Con cotizacion real",
            "id_quotation": "500",
        }, self.supervisor)

        self.assertEqual(500, creado["id_quotation"])
        self.assertIsNone(creado["quotation_reference"])

    def test_a_quotation_already_linked_to_another_active_project_is_rejected(self):
        self._invoice(501)
        create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Primero en tomarla",
            "id_quotation": "501",
        }, self.supervisor)

        with self.assertRaises(AppError) as fallo:
            create_project({
                "id_customer_supplier": 1,
                "proyect_description": "Segundo, choca",
                "id_quotation": "501",
            }, self.supervisor)

        self.assertEqual("errors.quotation_already_linked", fallo.exception.message_key)

    def test_a_quotation_linked_to_a_deleted_project_can_be_reused(self):
        self._invoice(502)
        primero = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Se va a borrar",
            "id_quotation": "502",
        }, self.supervisor)
        delete_project(primero["id_proyect"], self.supervisor)

        segundo = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Reusa la cotizacion",
            "id_quotation": "502",
        }, self.supervisor)

        self.assertEqual(502, segundo["id_quotation"])

    def test_updating_a_project_without_touching_the_quotation_keeps_it(self):
        self._invoice(503)
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Con cotizacion",
            "id_quotation": "503",
        }, self.supervisor)

        actualizado = update_project(creado["id_proyect"], {"title": "Nuevo titulo"}, self.supervisor)

        self.assertEqual(503, actualizado["id_quotation"])

    def test_an_inexistent_customer_contact_is_rejected(self):
        with self.assertRaises(AppError) as fallo:
            create_project({
                "id_customer_supplier": 1,
                "proyect_description": "Con contacto inventado",
                "id_customer_contact": 999999,
            }, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)

    def test_the_supervisor_cannot_be_assigned_from_the_payload(self):
        """Se TOMA, no se asigna.

        Era un desplegable del formulario, o sea que quien capturaba la orden
        repartia el trabajo del taller desde su escritorio.
        """
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Con supervisor impuesto",
            "id_supervisor": 31,
        }, self.supervisor)

        self.assertIsNone(creado["id_supervisor"])

        update_project(creado["id_proyect"], {"id_supervisor": 31}, self.supervisor)

        self.assertIsNone(
            get_project_detail(creado["id_proyect"], self.supervisor)["id_supervisor"])

    def test_the_leader_is_always_whoever_created_the_project(self):
        """Se podia levantar una orden a nombre de otra persona."""
        creado = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "A nombre de otro",
            "leader": 41,
        }, self.supervisor)

        self.assertEqual(self.supervisor["id_user"], creado["leader"])
        self.assertEqual(self.supervisor["id_user"], creado["created_by"])

    def test_updating_the_work_order_fields_validates_them_too(self):
        creado = self._create()

        with self.assertRaises(AppError) as fallo:
            update_project(creado["id_proyect"], {"id_customer_contact": 999999}, self.supervisor)

        self.assertEqual("errors.not_found", fallo.exception.message_key)


class TestElSupervisorTomaElProyecto(TestProjectWorkflowService):
    """El proyecto no se asigna: lo toma quien lo va a sacar adelante.

    `id_supervisor` era un desplegable del formulario, o sea que quien
    capturaba la orden repartia el trabajo del taller desde su escritorio.
    Ahora el proyecto nace libre y lo toma quien tiene la capacidad
    `project_execution` -- hoy el rol Jefe de taller (`self.workshop`).
    """

    def _autorizado(self, title="Para tomar"):
        """Un proyecto ya autorizado, que es lo que el taller ve.

        Gerente lo autoriza directo desde Borrador -- Supervisor ya no tiene
        la puerta de "enviar a revision" (decision de negocio, ver
        `transition_project`).
        """
        creado = self._create(title=title)
        transition_project(creado["id_proyect"], {"status": "authorized"}, self.manager)
        return creado["id_proyect"]

    def test_the_workshop_cannot_write_a_task_of_a_project_it_does_not_hold(self):
        """Ver un proyecto libre (para poder tomarlo) no autoriza a mover sus tareas."""
        from app.services.project_management_service import require_task_access

        id_proyect = self._autorizado()
        self._add_task(id_proyect)
        with transaction_context() as db:
            id_task = db.query(Task).filter(Task.id_proyect == id_proyect).one().id_task

        require_task_access(id_task, self.workshop)
        with self.assertRaises(AppError) as fallo:
            require_task_access(id_task, self.workshop, escribe=True)
        self.assertEqual("errors.project_not_taken_by_actor", fallo.exception.message_key)

        take_project(id_proyect, self.workshop)
        require_task_access(id_task, self.workshop, escribe=True)

    def test_the_workshop_takes_a_free_project(self):
        id_proyect = self._autorizado()

        tomado = take_project(id_proyect, self.workshop)

        self.assertEqual(self.workshop["id_user"], tomado["id_supervisor"])

    def test_it_is_written_in_the_file(self):
        """Quien lo tenia cuando paso lo que paso se lee en el expediente."""
        id_proyect = self._autorizado()

        take_project(id_proyect, self.workshop)

        with transaction_context() as db:
            eventos = [e.event_type for e in db.query(ProyectEvent)
                       .filter(ProyectEvent.id_proyect == id_proyect).all()]
        self.assertIn("taken", eventos)

    def test_whoever_cannot_execute_cannot_take(self):
        """Sin la capacidad no se toma, aunque se pueda ver el proyecto."""
        id_proyect = self._autorizado()

        with self.assertRaises(AppError) as fallo:
            take_project(id_proyect, self.supervisor)

        self.assertEqual("errors.permission_denied", fallo.exception.message_key)

    def test_a_taken_project_is_not_taken_again(self):
        """Quitarselo a otro seria reasignar, y eso no es tomar.

        Desde la correccion de visibilidad (2026-09-29, commit 2013b4c):
        `otro_taller` ni siquiera VE un proyecto que ya tomo OTRO Jefe de
        taller (`_scoped_query`, scope "execution", ya no incluye lo tomado
        por alguien mas). `take_project` llama a `_get_visible_project`
        primero, asi que el 404 llega antes de que la regla de
        "ya esta tomado" tenga oportunidad de hablar -- es el mismo
        resultado que ver cualquier otro recurso fuera de alcance, no un
        caso especial de este flujo.
        """
        id_proyect = self._autorizado()
        take_project(id_proyect, self.workshop)
        otro_taller = {"id_user": 32, "id_permission": 301}

        with self.assertRaises(AppError) as fallo:
            take_project(id_proyect, otro_taller)

        self.assertEqual("errors.resource_not_found", fallo.exception.message_key)

    def test_taking_it_twice_is_the_same_as_taking_it_once(self):
        id_proyect = self._autorizado()
        take_project(id_proyect, self.workshop)

        tomado = take_project(id_proyect, self.workshop)

        self.assertEqual(self.workshop["id_user"], tomado["id_supervisor"])

    def test_whoever_has_it_releases_it_and_another_takes_it(self):
        """Sin soltar, equivocarse de proyecto lo dejaba ocupado para siempre."""
        id_proyect = self._autorizado()
        take_project(id_proyect, self.workshop)
        otro_taller = {"id_user": 32, "id_permission": 301}

        release_project(id_proyect, self.workshop)
        tomado = take_project(id_proyect, otro_taller)

        self.assertEqual(32, tomado["id_supervisor"])

    def test_nobody_else_releases_what_they_do_not_have(self):
        """Mismo motivo que arriba: `otro_taller` ya no ve este proyecto
        (correccion de visibilidad, commit 2013b4c), asi que `release_project`
        -que tambien pasa por `_get_visible_project` primero- da 404 antes de
        llegar al candado de "no es tuyo"."""
        id_proyect = self._autorizado()
        take_project(id_proyect, self.workshop)
        otro_taller = {"id_user": 32, "id_permission": 301}

        with self.assertRaises(AppError) as fallo:
            release_project(id_proyect, otro_taller)

        self.assertEqual("errors.resource_not_found", fallo.exception.message_key)
