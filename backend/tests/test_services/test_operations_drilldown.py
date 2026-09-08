"""El flujo de Operaciones: proyecto -> tarea -> nota, y el motivo se guarda.

Por que existe este archivo
---------------------------
Las tres cosas que fija son las que faltaban para poder recorrer el modulo de
arriba abajo:

* **el cambio de estatus de una tarea deja rastro.** `proyect_event` tiene una
  columna `id_task`, con indice, desde el principio, y nadie la escribia: el
  expediente del proyecto solo contaba lo que le pasaba al proyecto, asi que
  una tarea bloqueada no aparecia en ningun sitio y el motivo del bloqueo se
  perdia. Quien preguntaba "por que se paro esto" no tenia donde mirarlo.

* **la maquina de estados vale igual por el camino nuevo.** El endpoint de
  transicion no puede ser un atajo que se salte lo que ya validaba el PUT.

* **la nota se escribe desde su tarea.** `task_note.id_task` es NOT NULL, o sea
  que una nota no existe sin su tarea; antes solo se capturaba desde una
  pantalla aparte, eligiendo la tarea en un desplegable.
"""

from __future__ import annotations

from app.models.proyect_event import ProyectEvent
from app.models.session import transaction_context
from app.models.task import Task
from app.models.task_note import TaskNote
from app.services.incident_service import transition_incident
from app.services.task_service import add_task_note, transition_task
from app.utils.errors import AppError
from tests.test_services.test_operations_workflow import OperationsTestCase


ACTOR = {"id_user": 1, "is_superuser": True}


def _events(id_task=None):
    with transaction_context() as db:
        query = db.query(ProyectEvent).order_by(ProyectEvent.id_proyect_event)
        if id_task is not None:
            query = query.filter(ProyectEvent.id_task == id_task)
        return [
            {
                "event_type": row.event_type,
                "id_task": row.id_task,
                "id_proyect": row.id_proyect,
                "previous_status": row.previous_status,
                "new_status": row.new_status,
                "reason": row.reason,
                "content": row.content,
            }
            for row in query.all()
        ]


class TestTaskTransition(OperationsTestCase):

    def test_a_task_transition_lands_on_the_project_timeline(self):
        task = self.new_task()

        moved = transition_task(task["id_task"], {"status": "en_proceso"}, ACTOR)

        self.assertEqual("en_proceso", moved["task_status"])
        self.assertEqual(
            [{
                "event_type": "task_status_changed",
                "id_task": task["id_task"],
                "id_proyect": 30,
                "previous_status": "pendiente",
                "new_status": "en_proceso",
                "reason": None,
                "content": None,
            }],
            _events(id_task=task["id_task"]),
            "el cambio de estatus de una tarea tiene que quedar colgado de la "
            "tarea en el expediente del proyecto, que es donde se busca",
        )

    def test_the_reason_of_a_block_is_kept(self):
        """Bloquear sin motivo dejaba la tarea parada y sin explicacion."""
        task = self.new_task()
        transition_task(task["id_task"], {"status": "en_proceso"}, ACTOR)

        transition_task(
            task["id_task"],
            {"status": "bloqueada", "reason": "falta la refaccion"},
            ACTOR,
        )

        ultimo = _events(id_task=task["id_task"])[-1]
        self.assertEqual("bloqueada", ultimo["new_status"])
        self.assertEqual("falta la refaccion", ultimo["reason"])

    def test_a_block_without_a_reason_is_refused(self):
        task = self.new_task()
        transition_task(task["id_task"], {"status": "en_proceso"}, ACTOR)

        with self.assertRaises(AppError) as raised:
            transition_task(task["id_task"], {"status": "bloqueada"}, ACTOR)

        self.assertEqual(
            "errors.task_transition_reason_required", raised.exception.message_key
        )

    def test_the_state_machine_is_not_bypassed_by_the_new_endpoint(self):
        """De pendiente no se salta a terminada: es el mismo mapa que el PUT."""
        task = self.new_task()

        with self.assertRaises(AppError) as raised:
            transition_task(task["id_task"], {"status": "terminada"}, ACTOR)

        self.assertEqual(
            "errors.task_invalid_transition", raised.exception.message_key
        )

    def test_a_task_status_from_before_the_catalogue_can_be_regularised(self):
        """Un valor viejo no deja la tarea atascada: se puede llevar al catalogo."""
        task = self.new_task()
        with transaction_context() as db:
            db.get(Task, task["id_task"]).task_status = "lo que sea"

        moved = transition_task(task["id_task"], {"status": "en_proceso"}, ACTOR)

        self.assertEqual("en_proceso", moved["task_status"])


class TestTaskNote(OperationsTestCase):

    def test_a_note_is_written_from_its_task(self):
        task = self.new_task()

        note = add_task_note(
            task["id_task"], {"task_note_description": "se cambio el sello"}, ACTOR
        )

        with transaction_context() as db:
            rows = db.query(TaskNote).filter(TaskNote.id_task == task["id_task"]).all()
            self.assertEqual(1, len(rows))
            self.assertEqual("se cambio el sello", rows[0].task_note_description)
        self.assertEqual(task["id_task"], note["id_task"])

    def test_the_note_shows_up_on_the_project_timeline(self):
        """Sin esto habia que abrir las tareas una por una para saber que paso."""
        task = self.new_task()

        add_task_note(task["id_task"], {"task_note_description": "sin refaccion"}, ACTOR)

        self.assertEqual(
            [{
                "event_type": "task_note",
                "id_task": task["id_task"],
                "id_proyect": 30,
                "previous_status": None,
                "new_status": None,
                "reason": None,
                "content": "sin refaccion",
            }],
            _events(id_task=task["id_task"]),
        )

    def test_an_empty_note_is_refused(self):
        task = self.new_task()

        with self.assertRaises(AppError) as raised:
            add_task_note(task["id_task"], {"task_note_description": "   "}, ACTOR)

        self.assertEqual("errors.required_field", raised.exception.message_key)


class TestIncidentTransition(OperationsTestCase):

    def test_an_incident_moves_and_gets_its_close_date(self):
        incident = self.new_incident()

        moved = transition_incident(incident["id_incident"], {"status": "en_proceso"}, ACTOR)
        self.assertEqual("en_proceso", moved["incident_status"])

        closed = transition_incident(incident["id_incident"], {"status": "resuelta"}, ACTOR)
        self.assertEqual("resuelta", closed["incident_status"])
        self.assertIsNotNone(
            closed["close_date"],
            "cerrar sin fecha dejaba la incidencia sin cuando se resolvio",
        )

    def test_a_cancellation_without_a_reason_is_refused(self):
        incident = self.new_incident()

        with self.assertRaises(AppError) as raised:
            transition_incident(incident["id_incident"], {"status": "cancelada"}, ACTOR)

        self.assertEqual(
            "errors.incident_transition_reason_required", raised.exception.message_key
        )

    def test_the_reason_of_a_cancellation_is_kept_in_the_audit_log(self):
        """`incident` no tiene tabla de eventos; se usa la bitacora que ya hay."""
        from app.models.audit_log import AuditLog

        incident = self.new_incident()
        transition_incident(
            incident["id_incident"],
            {"status": "cancelada", "reason": "reportada por error"},
            ACTOR,
        )

        with transaction_context() as db:
            row = (
                db.query(AuditLog)
                .filter(AuditLog.event_type == "incident_transition")
                .one()
            )
            self.assertEqual("cancelada", row.action)
            self.assertEqual("reportada por error", row.metadata_json["reason"])
            self.assertEqual("abierta", row.metadata_json["previous_status"])

    def test_a_closed_incident_does_not_move_again(self):
        incident = self.new_incident(incident_status="cerrada")

        with self.assertRaises(AppError) as raised:
            transition_incident(incident["id_incident"], {"status": "en_proceso"}, ACTOR)

        self.assertEqual(
            "errors.incident_invalid_transition", raised.exception.message_key
        )
