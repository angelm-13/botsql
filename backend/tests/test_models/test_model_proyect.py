from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.proyect import Proyect


class TestProyectModel(BackendTestCase):
    def test_create_serialize_summary_delete_proyect(self):
        with transaction_context() as session:
            item = build_model(Proyect,
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
