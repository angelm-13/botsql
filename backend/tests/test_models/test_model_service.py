from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.service import Service


class TestServiceModel(BackendTestCase):
    def test_create_serialize_summary_delete_service(self):
        with transaction_context() as session:
            item = build_model(Service,
            service_description='test description',
            average_time_cost=10.5,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
