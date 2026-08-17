from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.task_type import TaskType


class TestTaskTypeModel(BackendTestCase):
    def test_create_serialize_summary_delete_task_type(self):
        with transaction_context() as session:
            item = build_model(TaskType,
            task_type_description='test permission description',
            task_type_scope='test permission description',
            task_type_limit='test permission description',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
