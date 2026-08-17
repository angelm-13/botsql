from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.nm_template_task import NmTemplateTask


class TestNmTemplateTaskModel(BackendTestCase):
    def test_create_serialize_summary_delete_nm_template_task(self):
        with transaction_context() as session:
            item = NmTemplateTask(
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
