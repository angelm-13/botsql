from __future__ import annotations

from app.services.task_service import DEFAULT_FASE, TaskService
from app.utils.errors import AppError
from tests.test_services.test_operations_workflow import OperationsTestCase


class TestTaskService(OperationsTestCase):
    """CRUD basico de tareas.

    Antes esta prueba capturaba `task_status='test state'`, `priority='test
    priority'` y responsables inexistentes, y pasaba porque el servicio no
    validaba nada. Ahora usa datos validos.
    """

    def test_crud_service_task(self):
        created = TaskService.create({
            'task_code': 'C1',
            'start_date': '2026-01-15T12:00:00',
            'duration': 10.5,
            'type': 'business',
            'owner': 7, 'validation': 7,
            'dependency': 1,
            'task_description': 'test description',
            'estimated_effort': 'test estimated_effort',
            'task_status': 'pendiente',
            'fase': 'en_proceso',
            'priority': 'media',
            'title': 'test titulo',
            'id_proyect': 30,
            'created_by': 1,
        })
        self.assertIsNotNone(created)
        self.assertEqual('pendiente', created['task_status'])
        self.assertEqual('media', created['priority'])

        page = TaskService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def test_a_blank_fase_still_gets_the_default(self):
        """`TaskPage.jsx` siempre manda la llave 'fase' -vacia si nadie toco
        el select-, asi que `setdefault` nunca se disparaba y la tarea nacia
        con `fase=NULL`: el tablero kanban del taller agrupa por fase, y NULL
        no entra en ninguna columna esperada. Hallazgo de la auditoria de
        seguridad del 2026-10-06."""
        created = TaskService.create({
            'task_description': 'test description',
            'id_proyect': 30,
            'owner': 7, 'validation': 7,
            'dependency': 1,
            'created_by': 1,
            'fase': '',
        })

        self.assertEqual(DEFAULT_FASE, created['fase'])

    def test_placeholder_values_no_longer_pass(self):
        for field, value in (
            ('task_status', 'test state'), ('priority', 'test priority'), ('fase', 'test fase'),
        ):
            with self.subTest(field=field), self.assertRaises(AppError):
                TaskService.create({
                    'task_description': 'test description',
                    'id_proyect': 30,
                    'owner': 7, 'validation': 7,
                    'dependency': 1,
                    'created_by': 1,
                    field: value,
                })
