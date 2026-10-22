from __future__ import annotations

from app.models.entity_permission import EntityPermission
from app.models.proyect import Proyect
from app.models.session import transaction_context
from app.services.project_management_service import (
    add_project_payment,
    create_project,
    delete_project_payment,
    get_project_detail,
    list_projects,
    settle_project_payment,
    transition_management,
    update_project,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestProjectPriorityAndTotalCost(BackendTestCase):
    """`priority`/`total_cost` (y el `collection_status` derivado) son
    exclusivos de Gerencia -- candado real en el backend, no solo de UI. Ver
    el comentario de PROJECT_MANAGEMENT_ONLY_FIELDS en
    project_management_service.py.
    """

    def setUp(self):
        super().setUp()
        self.supervisor = {"id_user": 11, "id_permission": 101}
        self.manager = {"id_user": 21, "id_permission": 201}
        with transaction_context() as db:
            db.add_all([
                EntityPermission(
                    id_permission=201, entity_name="project_authorization",
                    scope_read=4, created_by=21,
                ),
                # Editar lo manda `scope_update` (Gestor): Propios para quien
                # levanta proyectos.
                EntityPermission(
                    id_permission=101, entity_name="proyect",
                    scope_update=1, created_by=11,
                ),
            ])

    def _create(self, actor, **extra):
        return create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo de fabricación",
            "title": "Proyecto",
            **extra,
        }, actor)

    def test_supervisor_cannot_set_priority_or_total_cost_on_create(self):
        project = self._create(self.supervisor, priority="alta", total_cost=1000)

        self.assertNotIn("priority", project)
        self.assertNotIn("total_cost", project)
        with transaction_context() as db:
            stored = db.get(Proyect, project["id_proyect"])
            self.assertIsNone(stored.priority)
            self.assertIsNone(stored.total_cost)

    def test_manager_can_set_priority_and_total_cost_on_create(self):
        # Gerencia ya no crea proyectos (correccion de negocio 2026-09-28:
        # solo Supervisor levanta la orden) -- lo crea el Supervisor y
        # Gerencia le pone prioridad/costo total enseguida, via update.
        project = self._create(self.supervisor)

        result = update_project(project["id_proyect"], {"priority": "alta", "total_cost": 1000}, self.manager)

        self.assertEqual(result["priority"], "alta")
        self.assertEqual(result["total_cost"], 1000)

    def test_invalid_priority_is_rejected(self):
        project = self._create(self.supervisor)
        with self.assertRaises(AppError) as raised:
            update_project(project["id_proyect"], {"priority": "urgente"}, self.manager)
        self.assertEqual("errors.invalid_field", raised.exception.message_key)

    def test_negative_total_cost_is_rejected(self):
        project = self._create(self.supervisor)
        with self.assertRaises(AppError) as raised:
            update_project(project["id_proyect"], {"total_cost": -1}, self.manager)
        self.assertEqual("errors.invalid_field", raised.exception.message_key)

    def test_supervisor_update_silently_ignores_management_only_fields(self):
        # El proyecto lo crea el Supervisor (para que pueda verlo/editarlo
        # despues -- el alcance de "ownership" solo ve lo propio) y Gerencia
        # ya le puso un valor antes, para comprobar que el intento posterior
        # del Supervisor no lo pisa.
        project = self._create(self.supervisor)
        update_project(project["id_proyect"], {"priority": "baja", "total_cost": 500}, self.manager)

        result = update_project(
            project["id_proyect"],
            {"priority": "alta", "total_cost": 999, "title": "Actualizado"},
            self.supervisor,
        )

        self.assertNotIn("priority", result)
        self.assertNotIn("total_cost", result)
        with transaction_context() as db:
            stored = db.get(Proyect, project["id_proyect"])
            self.assertEqual(stored.priority, "baja")
            self.assertEqual(float(stored.total_cost), 500.0)
            # Los campos que si le pertenecen a Supervisor si se guardan --
            # el candado es exclusivo de priority/total_cost.
            self.assertEqual(stored.title, "Actualizado")

    def test_manager_update_overwrites_priority_and_total_cost(self):
        project = self._create(self.supervisor)
        update_project(project["id_proyect"], {"priority": "baja", "total_cost": 500}, self.manager)

        result = update_project(project["id_proyect"], {"priority": "media", "total_cost": 750}, self.manager)

        self.assertEqual(result["priority"], "media")
        self.assertEqual(result["total_cost"], 750)

    def test_supervisor_never_sees_management_only_fields_in_list_or_detail(self):
        # Lo crea el Supervisor -para que pueda consultarlo despues- y
        # Gerencia le agrega prioridad/costo total aparte.
        project = self._create(self.supervisor)
        update_project(project["id_proyect"], {"priority": "alta", "total_cost": 500}, self.manager)

        detail = get_project_detail(project["id_proyect"], self.supervisor)
        listing = list_projects(self.supervisor)

        self.assertNotIn("priority", detail)
        self.assertNotIn("total_cost", detail)
        self.assertNotIn("collection_status", detail)
        self.assertNotIn("priority", listing["items"][0])
        self.assertNotIn("collection_status", listing["items"][0])

    def test_collection_status_without_total_cost_is_none(self):
        project = self._create(self.supervisor)

        detail = get_project_detail(project["id_proyect"], self.manager)

        self.assertIsNone(detail["collection_status"])

    def test_collection_status_pendiente_cobrado_excedido(self):
        project = self._create(self.supervisor)
        project_id = project["id_proyect"]
        update_project(project_id, {"total_cost": 1000}, self.manager)

        self.assertEqual(get_project_detail(project_id, self.manager)["collection_status"], "pendiente")

        add_project_payment(project_id, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)
        self.assertEqual(get_project_detail(project_id, self.manager)["collection_status"], "cobrado")

        add_project_payment(project_id, {
            "payment_date": "2026-09-10", "amount": 200, "paid_at": "2026-09-10",
        }, self.manager)
        self.assertEqual(get_project_detail(project_id, self.manager)["collection_status"], "excedido")

    def test_list_projects_reports_collection_status_per_project(self):
        project = self._create(self.supervisor)
        update_project(project["id_proyect"], {"total_cost": 1000}, self.manager)
        add_project_payment(project["id_proyect"], {
            "payment_date": "2026-09-01", "amount": 400, "paid_at": "2026-09-01",
        }, self.manager)

        listing = list_projects(self.manager)

        self.assertEqual(listing["items"][0]["collection_status"], "pendiente")


class TestManagementStatusFollowsCollection(BackendTestCase):
    """`management_status` ya no admite "cobrado" como destino manual -- lo
    mueve solo `_sync_management_status_with_collection`, en los dos
    sentidos, siguiendo el mismo costo total/parcialidades que la columna de
    estado de cobro. Ver el comentario de MANAGEMENT_TRANSITIONS.
    """

    def setUp(self):
        super().setUp()
        self.supervisor = {"id_user": 11, "id_permission": 101}
        self.manager = {"id_user": 21, "id_permission": 201}
        with transaction_context() as db:
            db.add_all([
                EntityPermission(
                    id_permission=201, entity_name="project_authorization",
                    scope_read=4, created_by=21,
                ),
                # Editar lo manda `scope_update` (Gestor): Propios para quien
                # levanta proyectos.
                EntityPermission(
                    id_permission=101, entity_name="proyect",
                    scope_update=1, created_by=11,
                ),
            ])

    def _create(self, **extra):
        # Gerencia ya no crea proyectos (correccion de negocio 2026-09-28):
        # lo levanta el Supervisor, y Gerencia le pone `total_cost` (si lo
        # pide esta prueba) enseguida, via update -- antes de autorizarlo.
        project = create_project({
            "id_customer_supplier": 1,
            "proyect_description": "Trabajo de fabricación",
            "title": "Proyecto",
        }, self.supervisor)
        if extra:
            project = update_project(project["id_proyect"], extra, self.manager)
        return project

    def test_manual_transition_to_cobrado_is_rejected(self):
        project = self._create()["id_proyect"]
        transition_management(project, {"management_status": "autorizado"}, self.manager)

        with self.assertRaises(AppError) as raised:
            transition_management(project, {"management_status": "cobrado"}, self.manager)
        self.assertEqual("errors.project_invalid_management_transition", raised.exception.message_key)

    def test_full_collection_moves_authorized_to_cobrado_automatically(self):
        project = self._create(total_cost=1000)["id_proyect"]
        transition_management(project, {"management_status": "autorizado"}, self.manager)

        add_project_payment(project, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)

        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "cobrado")

    def test_unsettling_a_payment_reverts_cobrado_back_to_authorized(self):
        project = self._create(total_cost=1000)["id_proyect"]
        transition_management(project, {"management_status": "autorizado"}, self.manager)
        pago = add_project_payment(project, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)
        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "cobrado")

        settle_project_payment(pago["id_proyect_payment"], {"paid_at": ""}, self.manager)

        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "autorizado")

    def test_deleting_a_paid_installment_reverts_cobrado_back_to_authorized(self):
        project = self._create(total_cost=1000)["id_proyect"]
        transition_management(project, {"management_status": "autorizado"}, self.manager)
        pago = add_project_payment(project, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)
        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "cobrado")

        delete_project_payment(pago["id_proyect_payment"], self.manager)

        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "autorizado")

    def test_full_collection_before_authorization_does_not_skip_it(self):
        """pendiente_orden_compra no salta directo a cobrado aunque el pago
        ya haya entrado -- Gerencia todavia no autorizo el proyecto.
        """
        project = self._create(total_cost=1000)["id_proyect"]

        add_project_payment(project, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)

        self.assertEqual(
            get_project_detail(project, self.manager)["management_status"],
            "pendiente_orden_compra",
        )

    def test_increasing_total_cost_after_full_collection_reverts_cobrado(self):
        """Cambiar el costo total tambien resincroniza -- no solo tocar una
        parcialidad."""
        project = self._create(total_cost=1000)["id_proyect"]
        transition_management(project, {"management_status": "autorizado"}, self.manager)
        add_project_payment(project, {
            "payment_date": "2026-09-01", "amount": 1000, "paid_at": "2026-09-05",
        }, self.manager)
        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "cobrado")

        update_project(project, {"total_cost": 5000}, self.manager)

        self.assertEqual(get_project_detail(project, self.manager)["management_status"], "autorizado")
