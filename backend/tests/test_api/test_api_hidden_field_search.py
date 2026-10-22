"""Filtrar, ordenar o buscar por un campo equivale a leerlo."""
from __future__ import annotations

from unittest.mock import patch

from app.models.customer_supplier import CustomerSupplier
from app.models.entity_permission import EntityPermission
from app.models.field import Field
from app.models.nm_field_permission import NmFieldPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase
from tests.model_factory import build_model


class TestHiddenFieldsDoNotLeakThroughTheList(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.actor = {"id_user": 11, "id_permission": 101, "id_proyect": 1}
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=101, entity_name="customer_supplier",
                                    scope_read=4, created_by=1))
            visible = build_model(Field, table_name="customer_supplier", field_name="name", created_by=1)
            db.add(visible)
            db.flush()
            db.add(NmFieldPermission(id_field=visible.id_field, id_permission=101,
                                     control_type="2", created_by=1))
            db.add(build_model(CustomerSupplier, name="Cliente Uno", type="client",
                               tax_id="SECRETRFC010101AB1"))

    def _get(self, query):
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            return self.client.get("/customer_supplier/" + query,
                                   headers={"Authorization": "Bearer hidden-field"})

    def test_a_visible_field_still_filters_and_searches(self):
        self.assertEqual(1, self.json(self._get("?name=Cliente"))["total"])
        self.assertEqual(1, self.json(self._get("?q=Cliente"))["total"])

    def test_a_hidden_field_does_not_filter_or_search(self):
        total = self.json(self._get("?q=ZZZ-NADA"))["total"]
        # Con el RFC oculto, buscarlo no distingue entre "existe" y "no existe".
        self.assertEqual(total, self.json(self._get("?q=SECRETRFC"))["total"])
        self.assertEqual(self.json(self._get(""))["total"],
                         self.json(self._get("?tax_id=ZZZ"))["total"])
