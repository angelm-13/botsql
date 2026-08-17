from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.task_service import TaskService


class TestTaskService(BackendTestCase):
    def test_crud_service_task(self):
        created = TaskService.create({'task_code': 'C1', 'start_date': 'datetime.now()', 'duration': 10.5, 'type': 'business', 'owner': 1, 'analyst': 1, 'dependency': 1, 'leader': 1, 'validation': 1, 'task_description': 'test description', 'estimated_effort': 'test estimated_effort', 'task_status': 'test state', 'fase': 'test fase', 'priority': 'test priority', 'title': 'test titulo', 'created_by': 1})
        self.assertIsNotNone(created)
        page = TaskService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
