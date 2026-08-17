from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.task_service import TaskService


class TestTaskService(BackendTestCase):
    def test_crud_service_task(self):
        created = TaskService.create(build_payload(TaskService, task_code='C1', start_date='2026-01-15T12:00:00', duration=10.5, type='business', owner=1, analyst=1, dependency=1, leader=1, validation=1, task_description='test description', estimated_effort='test estimated_effort', task_status='test state', fase='test fase', priority='test priority', title='test titulo', created_by=1))
        self.assertIsNotNone(created)
        page = TaskService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
