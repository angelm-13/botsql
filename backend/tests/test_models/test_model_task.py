from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.task import Task


class TestTaskModel(BackendTestCase):
    def test_create_serialize_summary_delete_task(self):
        with transaction_context() as session:
            item = build_model(Task,
            task_code='C1',
            start_date='2026-01-15T12:00:00',
            duration=10.5,
            type='business',
            owner=1,
            dependency=1,
            validation=1,
            task_description='test description',
            estimated_effort='test estimated_effort',
            task_status='test state',
            fase='en_espera',
            priority='test priority',
            title='test titulo',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
