from __future__ import annotations

from app.services.task_service import TaskService
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
            'owner': 7, 'analyst': 7, 'leader': 7, 'validation': 7,
            'dependency': 1,
            'task_description': 'test description',
            'estimated_effort': 'test estimated_effort',
            'task_status': 'pendiente',
            'fase': 'test fase',
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

    def test_placeholder_values_no_longer_pass(self):
        for field, value in (('task_status', 'test state'), ('priority', 'test priority')):
            with self.subTest(field=field), self.assertRaises(AppError):
                TaskService.create({
                    'task_description': 'test description',
                    'id_proyect': 30,
                    'owner': 7, 'analyst': 7, 'leader': 7, 'validation': 7,
                    'dependency': 1,
                    'created_by': 1,
                    field: value,
                })
