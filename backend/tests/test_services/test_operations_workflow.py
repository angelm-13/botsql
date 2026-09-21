"""Reglas de negocio de Operaciones: incidencias y tareas.

Los dos modulos eran un CRUD sin reglas. Estas pruebas fijan lo que ahora se
rechaza, y en particular que los registros capturados antes del catalogo de
estatus se puedan seguir editando y regularizar: rechazarlos habria dejado
datos existentes inaccesibles.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.models import (
    CustomerSupplier,
    Department,
    Incident,
    IncidentType,
    Level,
    Permission,
    Proyect,
    Status,
    Subdepartment,
    Task,
    User,
)
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.services.incident_service import IncidentService, list_incidents, require_incident_access
from app.services.operations_workflow import (
    normalize_incident_status,
    normalize_task_status,
)
from app.services.task_service import TaskService, task_is_closed
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OperationsTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # user.id_permission es obligatorio, y un permiso exige
            # departamento, subdepartamento y nivel: la cadena minima para
            # tener un responsable real al que asignar tareas.
            db.add_all([
                Department(id_department=1, department_description="Operaciones", created_by=1),
                Level(id_level=1, level_description="Operativo", created_by=1),
            ])
            db.flush()
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="Campo", id_department=1, created_by=1))
            db.flush()
            db.add_all([
                Permission(
                    id_permission=1, permission_description="Operador", authorized_by=1,
                    id_department=1, id_subdepartment=1, id_level=1, created_by=1,
                ),
                Status(
                    id_status=40, status_description="Activo", category="general",
                    is_terminal=False, sort_order="asc", created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=20, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1,
                ),
                IncidentType(id_incident_type=1, incident_type_description="Falla de equipo", created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(
                    id_proyect=30, id_customer_supplier=20, leader=1,
                    proyect_description="Proyecto abierto", proyect_status="in_progress", created_by=1,
                ),
                Proyect(
                    id_proyect=31, id_customer_supplier=20, leader=1,
                    proyect_description="Proyecto cerrado", proyect_status="completed", created_by=1,
                ),
                Proyect(
                    id_proyect=32, id_customer_supplier=20, leader=1,
                    proyect_description="Proyecto denegado", proyect_status="denied", created_by=1,
                ),
            ])
            db.flush()
            db.add(User(
                id_user=7, username="operador", email="operador@tyakxa.local",
                password="x", user_type="employee", full_name="Operador de Campo",
                id_permission=1, id_proyect=30, id_status=40, supervisor=1, created_by=1,
            ))

    def new_incident(self, **overrides):
        payload = {
            "incident_date": (_now() - timedelta(days=1)).isoformat(),
            "id_incident_type": 1,
            "id_user": 7,
            "created_by": 1,
        }
        payload.update(overrides)
        return IncidentService.create(payload, user_id=1)

    def new_task(self, **overrides):
        payload = {
            "task_description": "Tarea de prueba",
            "id_proyect": 30,
            "owner": 7, "analyst": 7, "leader": 7, "validation": 7,
            "dependency": 1,
            "created_by": 1,
        }
        payload.update(overrides)
        return TaskService.create(payload, user_id=1)


class TestIncidentRules(OperationsTestCase):
    def test_a_new_incident_starts_open(self):
        self.assertEqual("abierta", self.new_incident()["incident_status"])

    def test_a_status_outside_the_catalog_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_incident(incident_status="chidisima")

        self.assertEqual("errors.incident_status_invalid", raised.exception.message_key)

    def test_an_incident_cannot_be_closed_before_it_happened(self):
        with self.assertRaises(AppError) as raised:
            self.new_incident(
                incident_status="cerrada",
                close_date=(_now() - timedelta(days=10)).isoformat(),
            )

        self.assertEqual(
            "errors.incident_close_date_before_incident_date", raised.exception.message_key
        )

    def test_an_incident_cannot_happen_in_the_future(self):
        with self.assertRaises(AppError) as raised:
            self.new_incident(incident_date=(_now() + timedelta(days=30)).isoformat())

        self.assertEqual("errors.incident_date_in_the_future", raised.exception.message_key)

    def test_a_close_date_without_a_closed_status_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_incident(incident_status="abierta", close_date=_now().isoformat())

        self.assertEqual(
            "errors.incident_close_date_requires_closed_status", raised.exception.message_key
        )

    def test_closing_fills_the_close_date_when_it_is_missing(self):
        """Cerrar sin fecha dejaba la incidencia sin cuando se resolvio."""
        incident = self.new_incident()
        IncidentService.update(incident["id_incident"], {"incident_status": "en_proceso"}, user_id=1)
        closed = IncidentService.update(
            incident["id_incident"], {"incident_status": "resuelta"}, user_id=1
        )

        self.assertIsNotNone(closed["close_date"])

    def test_a_responsible_user_that_does_not_exist_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_incident(id_user=9999)

        self.assertEqual("validations.incident.id_user.invalid", raised.exception.message_key)

    def test_an_incident_type_that_does_not_exist_is_refused(self):
        with self.assertRaises(AppError):
            self.new_incident(id_incident_type=9999)

    def test_the_full_lifecycle_runs(self):
        incident = self.new_incident()["id_incident"]

        for target in ("en_proceso", "resuelta", "cerrada"):
            with self.subTest(target=target):
                result = IncidentService.update(incident, {"incident_status": target}, user_id=1)
                self.assertEqual(target, result["incident_status"])

    def test_illegal_jumps_are_refused(self):
        incident = self.new_incident()["id_incident"]

        with self.assertRaises(AppError) as raised:
            IncidentService.update(incident, {"incident_status": "cerrada"}, user_id=1)

        self.assertEqual("errors.incident_invalid_transition", raised.exception.message_key)

    def test_a_closed_incident_admits_no_further_change(self):
        incident = self.new_incident()["id_incident"]
        for target in ("en_proceso", "resuelta", "cerrada"):
            IncidentService.update(incident, {"incident_status": target}, user_id=1)

        with self.assertRaises(AppError):
            IncidentService.update(incident, {"incident_status": "en_proceso"}, user_id=1)

    def test_a_resolved_incident_can_be_reopened(self):
        """Si el problema volvio, hay que poder retomarla."""
        incident = self.new_incident()["id_incident"]
        IncidentService.update(incident, {"incident_status": "en_proceso"}, user_id=1)
        IncidentService.update(incident, {"incident_status": "resuelta"}, user_id=1)

        result = IncidentService.update(incident, {"incident_status": "en_proceso"}, user_id=1)

        self.assertEqual("en_proceso", result["incident_status"])

    def test_cancelling_requires_a_reason(self):
        incident = self.new_incident()["id_incident"]

        with self.assertRaises(AppError) as raised:
            IncidentService.update(incident, {"incident_status": "cancelada"}, user_id=1)
        self.assertEqual(
            "errors.incident_transition_reason_required", raised.exception.message_key
        )

        result = IncidentService.update(
            incident, {"incident_status": "cancelada", "note": "Duplicada"}, user_id=1
        )
        self.assertEqual("cancelada", result["incident_status"])

    def test_a_legacy_status_can_still_be_regularized(self):
        """Un registro anterior al catalogo debe poder corregirse."""
        incident = self.new_incident()["id_incident"]
        with transaction_context() as db:
            db.get(Incident, incident).incident_status = "lo_que_sea"

        result = IncidentService.update(incident, {"incident_status": "en_proceso"}, user_id=1)

        self.assertEqual("en_proceso", result["incident_status"])

    def test_editing_other_fields_leaves_a_legacy_status_alone(self):
        incident = self.new_incident()["id_incident"]
        with transaction_context() as db:
            db.get(Incident, incident).incident_status = "lo_que_sea"

        result = IncidentService.update(incident, {"note": "Nota nueva"}, user_id=1)

        self.assertEqual("lo_que_sea", result["incident_status"])


class TestTaskRules(OperationsTestCase):
    def test_a_new_task_starts_pending(self):
        self.assertEqual("pendiente", self.new_task()["task_status"])

    def test_a_status_outside_the_catalog_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_task(task_status="volando_en_ovni")

        self.assertEqual("errors.task_status_invalid", raised.exception.message_key)

    def test_a_responsible_user_that_does_not_exist_is_refused(self):
        """analyst, leader y validation son enteros sin llave foranea."""
        for field in ("owner", "analyst", "leader", "validation"):
            with self.subTest(field=field), self.assertRaises(AppError) as raised:
                self.new_task(**{field: 99999})
            self.assertEqual("errors.task_responsible_not_found", raised.exception.message_key)

    def test_a_negative_duration_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_task(duration=-500)

        self.assertEqual("errors.invalid_field", raised.exception.message_key)

    def test_zero_duration_is_allowed(self):
        self.assertIsNotNone(self.new_task(duration=0))

    def test_a_priority_outside_the_catalog_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.new_task(priority="URGENTISIMA")

        self.assertEqual("errors.task_priority_invalid", raised.exception.message_key)

    def test_priority_accepts_the_usual_spellings(self):
        for written, expected in (("high", "alta"), ("Normal", "media"), ("URGENTE", "urgente")):
            with self.subTest(written=written):
                self.assertEqual(expected, self.new_task(priority=written)["priority"])

    def test_no_new_task_in_a_closed_project(self):
        for project, status in ((31, "completed"), (32, "denied")):
            with self.subTest(status=status), self.assertRaises(AppError) as raised:
                self.new_task(id_proyect=project)
            self.assertEqual("errors.task_project_closed", raised.exception.message_key)

    def test_an_existing_task_can_be_closed_after_its_project_closed(self):
        """El proyecto puede cerrarse antes que su ultima tarea."""
        task = self.new_task()["id_task"]
        TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)
        with transaction_context() as db:
            db.get(Proyect, 30).proyect_status = "completed"

        result = TaskService.update(task, {"task_status": "terminada"}, user_id=1)

        self.assertEqual("terminada", result["task_status"])

    def test_the_full_lifecycle_runs(self):
        task = self.new_task()["id_task"]

        for target in ("en_proceso", "en_revision", "terminada"):
            with self.subTest(target=target):
                result = TaskService.update(task, {"task_status": target}, user_id=1)
                self.assertEqual(target, result["task_status"])

    def test_illegal_jumps_are_refused(self):
        task = self.new_task()["id_task"]

        with self.assertRaises(AppError) as raised:
            TaskService.update(task, {"task_status": "terminada"}, user_id=1)

        self.assertEqual("errors.task_invalid_transition", raised.exception.message_key)

    def test_blocking_requires_a_reason(self):
        task = self.new_task()["id_task"]
        TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)

        with self.assertRaises(AppError) as raised:
            TaskService.update(task, {"task_status": "bloqueada"}, user_id=1)
        self.assertEqual("errors.task_transition_reason_required", raised.exception.message_key)

        result = TaskService.update(
            task, {"task_status": "bloqueada", "note": "Falta material"}, user_id=1
        )
        self.assertEqual("bloqueada", result["task_status"])

    def test_a_blocked_task_returns_to_progress(self):
        task = self.new_task()["id_task"]
        TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)
        TaskService.update(task, {"task_status": "bloqueada", "note": "Falta material"}, user_id=1)

        result = TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)

        self.assertEqual("en_proceso", result["task_status"])

    def test_review_can_send_the_task_back(self):
        task = self.new_task()["id_task"]
        TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)
        TaskService.update(task, {"task_status": "en_revision"}, user_id=1)

        result = TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)

        self.assertEqual("en_proceso", result["task_status"])

    def test_a_finished_task_admits_no_further_change(self):
        task = self.new_task()["id_task"]
        TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)
        TaskService.update(task, {"task_status": "terminada"}, user_id=1)

        with self.assertRaises(AppError):
            TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)

    def test_a_legacy_status_can_still_be_regularized(self):
        task = self.new_task()["id_task"]
        with transaction_context() as db:
            db.get(Task, task).task_status = "volando_en_ovni"

        result = TaskService.update(task, {"task_status": "en_proceso"}, user_id=1)

        self.assertEqual("en_proceso", result["task_status"])

    def test_task_is_closed_helper(self):
        with transaction_context() as db:
            self.assertFalse(task_is_closed(Task(task_status="en_proceso")))
            self.assertTrue(task_is_closed(Task(task_status="terminada")))
            self.assertTrue(task_is_closed(Task(task_status="cancelada")))


class TestStatusNormalization(unittest.TestCase):
    """El estatus se capturaba a mano, asi que llega escrito de muchas formas."""

    def test_incident_spellings(self):
        for written, expected in (
            ("EN PROCESO", "en_proceso"),
            ("en-proceso", "en_proceso"),
            ("Resuelto", "resuelta"),
            ("cerrado", "cerrada"),
            ("  abierto  ", "abierta"),
            ("nueva", "abierta"),
        ):
            with self.subTest(written=written):
                self.assertEqual(expected, normalize_incident_status(written))

    def test_task_spellings(self):
        for written, expected in (
            ("Por hacer", "pendiente"),
            ("DOING", "en_proceso"),
            ("en revision", "en_revision"),
            ("Done", "terminada"),
            ("completada", "terminada"),
            ("bloqueado", "bloqueada"),
        ):
            with self.subTest(written=written):
                self.assertEqual(expected, normalize_task_status(written))

    def test_an_empty_status_stays_empty(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                self.assertEqual("", normalize_task_status(value))
                self.assertEqual("", normalize_incident_status(value))

    def test_an_unknown_status_is_returned_for_the_caller_to_judge(self):
        self.assertEqual("lo_que_sea", normalize_task_status("lo que sea"))


if __name__ == "__main__":
    unittest.main()


class TestIncidentScope(OperationsTestCase):
    """Quien ve cada incidencia.

    Antes cualquiera con permiso de lectura veia las incidencias de toda la
    empresa. Ahora una persona alcanza las suyas -las que reporto, las que
    atiende y las que lidera- y quien supervisa las ve todas.
    """

    ATIENDE = {"id_user": 7, "id_permission": 700}
    AJENO = {"id_user": 8, "id_permission": 700}
    SUPERVISA = {"id_user": 9, "id_permission": 701}

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # Los otros dos participantes tienen que existir: el servicio
            # comprueba que el responsable y el lider sean usuarios reales.
            db.add_all([
                User(
                    id_user=8, username="ajeno", email="ajeno@tyakxa.local",
                    password="x", user_type="employee", full_name="Persona Ajena",
                    id_permission=1, id_proyect=30, id_status=40, supervisor=1, created_by=1,
                ),
                User(
                    id_user=9, username="supervisa", email="sup2@tyakxa.local",
                    password="x", user_type="employee", full_name="Quien Supervisa",
                    id_permission=1, id_proyect=30, id_status=40, supervisor=1, created_by=1,
                ),
                EntityPermission(
                    id_permission=701, entity_name="incident_supervision",
                    scope_read=4, created_by=1,
                ),
            ])

    def _incident(self, **overrides):
        payload = {
            "incident_date": (_now() - timedelta(days=1)).isoformat(),
            "id_incident_type": 1,
            "id_user": 7,
            "created_by": 7,
        }
        payload.update(overrides)
        return IncidentService.create(payload, user_id=payload["created_by"])["id_incident"]

    def test_a_person_sees_the_incident_they_attend(self):
        self._incident(id_user=7)

        result = list_incidents(self.ATIENDE)

        self.assertEqual(1, result["total"])

    def test_a_person_sees_the_incident_they_lead(self):
        self._incident(id_user=8, id_lider=7, created_by=8)

        self.assertEqual(1, list_incidents(self.ATIENDE)["total"])

    def test_a_person_sees_the_incident_they_reported(self):
        self._incident(id_user=8, created_by=7)

        self.assertEqual(1, list_incidents(self.ATIENDE)["total"])

    def test_a_person_does_not_see_someone_elses_incident(self):
        self._incident(id_user=8, created_by=8)

        self.assertEqual(0, list_incidents(self.ATIENDE)["total"])

    def test_a_supervisor_sees_every_incident(self):
        self._incident(id_user=7, created_by=7)
        self._incident(id_user=8, created_by=8)

        self.assertEqual(2, list_incidents(self.SUPERVISA)["total"])

    def test_reading_someone_elses_incident_says_it_does_not_exist(self):
        """No se responde 'no puedes': quien no participa tampoco debe saber
        que la incidencia existe."""
        ajena = self._incident(id_user=8, created_by=8)

        with self.assertRaises(AppError) as raised:
            require_incident_access(ajena, self.ATIENDE)

        self.assertEqual("errors.resource_not_found", raised.exception.message_key)
        self.assertEqual(404, raised.exception.status_code)

    def test_a_participant_can_open_their_incident(self):
        propia = self._incident(id_user=7, created_by=7)

        self.assertEqual(propia, require_incident_access(propia, self.ATIENDE).id_incident)

    def test_a_supervisor_opens_any_incident(self):
        ajena = self._incident(id_user=8, created_by=8)

        self.assertEqual(ajena, require_incident_access(ajena, self.SUPERVISA).id_incident)

    def test_an_actor_without_identity_sees_nothing(self):
        self._incident(id_user=7, created_by=7)

        self.assertEqual(0, list_incidents({})["total"])

    def test_the_list_can_be_filtered_by_status(self):
        primera = self._incident(id_user=7, created_by=7)
        self._incident(id_user=7, created_by=7)
        IncidentService.update(primera, {"incident_status": "en_proceso"}, user_id=7)

        result = list_incidents(self.ATIENDE, filters={"incident_status": "en_proceso"})

        self.assertEqual(1, result["total"])
        self.assertEqual(primera, result["items"][0]["id_incident"])
