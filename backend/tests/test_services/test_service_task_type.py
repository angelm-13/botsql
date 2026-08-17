from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.task_type_service import TaskTypeService


class TestTaskTypeService(BackendTestCase):
    def test_crud_service_task_type(self):
        created = TaskTypeService.create(build_payload(TaskTypeService, {'task_type_description': 'test permission description', 'task_type_scope': 'test permission description', 'task_type_limit': 'test permission description', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = TaskTypeService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
