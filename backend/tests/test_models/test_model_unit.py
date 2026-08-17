from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.unit import Unit


class TestUnitModel(BackendTestCase):
    def test_create_serialize_summary_delete_unit(self):
        with transaction_context() as session:
            item = Unit(
            unit_code='test description',
            unit_name='test description',
            unit_category='test description',
            is_active=True,
            symbol='test description',
            measurement_system='metric',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
