from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.task_note_service import TaskNoteService


class TestTaskNoteService(BackendTestCase):
    def test_crud_service_task_note(self):
        created = TaskNoteService.create(build_payload(TaskNoteService, {'date': '2026-01-15T12:00:00', 'task_note_description': 'test description', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = TaskNoteService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
