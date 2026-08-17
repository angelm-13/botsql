from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.task_note_service import TaskNoteService


class TestTaskNoteService(BackendTestCase):
    def test_crud_service_task_note(self):
        created = TaskNoteService.create({'date': 'datetime.now()', 'task_note_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = TaskNoteService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
