from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.product import Product


class TestProductModel(BackendTestCase):
    def test_create_serialize_summary_delete_product(self):
        with transaction_context() as session:
            item = build_model(Product,
            gross_price=10.5,
            color='test color',
            is_directly_related_to_product_service=True,
            product_status='test state',
            path_imagen='test path_imagen',
            product_code='test code',
            note='test note',
            created_by=1,
            descripcion='test_descripcion',
            cantidad='test_cantidad'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
