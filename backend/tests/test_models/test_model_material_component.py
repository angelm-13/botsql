from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.material_component import MaterialComponent


class TestMaterialComponentModel(BackendTestCase):
    def test_create_serialize_summary_delete_material_component(self):
        with transaction_context() as session:
            item = build_model(MaterialComponent,
            relation=10.5,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
