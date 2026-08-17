from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.proyect import Proyect


class TestProyectModel(BackendTestCase):
    def test_create_serialize_summary_delete_proyect(self):
        with transaction_context() as session:
            item = Proyect(
            leader=1,
            proyect_description='test description',
            title='test title',
            proyect_status='test state',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
