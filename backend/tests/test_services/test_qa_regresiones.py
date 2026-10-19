"""Regresiones de la ronda de QA del 2026-10-15."""
from __future__ import annotations

import unittest

from app.services.appointment_service import _parse_time
from app.services.customer_supplier_service import CustomerSupplierService
from app.services.user_service import UserService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestRegresionesDeQA(BackendTestCase):
    def test_free_text_search_never_looks_inside_passwords(self):
        condicion = str(UserService._busqueda_libre("$2b$12$"))
        self.assertNotIn("password", condicion.lower())
        self.assertIn("username", condicion.lower())  # sigue buscando en lo demas

    def test_a_non_finite_credit_limit_is_a_400(self):
        for valor in ("NaN", "Infinity", "1e400"):
            with self.subTest(valor=valor), self.assertRaises(AppError) as e:
                CustomerSupplierService.create(
                    {"name": "X", "type": "client", "credit_limit": valor}, user_id=1)
            self.assertEqual(400, e.exception.status_code)

    def test_an_availability_time_with_a_timezone_is_a_400(self):
        with self.assertRaises(AppError) as e:
            _parse_time("09:00+02:00", "start_time")
        self.assertEqual(400, e.exception.status_code)
        self.assertEqual("09:00", _parse_time("09:00", "start_time").strftime("%H:%M"))

    def test_pos_decimals_must_be_finite_and_inventory_quantities_bounded(self):
        from app.services.inventory_service import _integer_quantity
        from app.services.pos_service import _decimal

        for valor in ("NaN", "Infinity"):
            with self.subTest(valor=valor), self.assertRaises(AppError) as e:
                _decimal(valor, "amount")
            self.assertEqual(422, e.exception.status_code)
        with self.assertRaises(AppError) as e:
            _integer_quantity(10**30)
        self.assertEqual(400, e.exception.status_code)
        self.assertEqual(5, _integer_quantity(5))

    def test_a_non_object_json_body_is_a_400_not_a_500(self):
        from unittest.mock import patch

        actor = {"id_user": 1, "is_superuser": True, "id_proyect": 1}
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            for ruta in ("/logistics_unit/", "/product/1/inventory-movements"):
                with self.subTest(ruta=ruta):
                    r = self.client.post(ruta, json=[1], headers={"Authorization": "Bearer x"})
                    self.assertLess(r.status_code, 500, r.get_data(as_text=True))

    def test_a_principal_customer_without_rfc_is_not_saved_at_all(self):
        from app.models.customer_supplier import CustomerSupplier
        from app.models.session import transaction_context

        with self.assertRaises(AppError) as e:
            CustomerSupplierService.create(
                {"name": "SinRFC", "type": "client", "is_principal": True}, user_id=1)
        self.assertEqual(400, e.exception.status_code)
        with transaction_context() as db:
            self.assertEqual(0, db.query(CustomerSupplier).filter(
                CustomerSupplier.name == "SinRFC").count())

    def test_a_put_cannot_rewrite_the_primary_key(self):
        from app.services.brand_service import BrandService

        marca = BrandService.create({"brand_description": "Marca QA"}, user_id=1)
        id_marca = marca["id_brand"]
        BrandService.update(id_marca, {"id_brand": 9999, "brand_description": "Otra"}, user_id=1)
        self.assertEqual("Otra", BrandService.get(id_marca)["brand_description"])

    def test_contacts_reject_blank_names_bad_status_and_moving_into_a_duplicate(self):
        from app.models.customer_supplier import CustomerSupplier
        from app.models.session import transaction_context
        from app.services.customer_contact_service import CustomerContactService
        from tests.model_factory import build_model

        with transaction_context() as db:
            for n in (10, 20):
                fila = build_model(CustomerSupplier, name="C%d" % n, type="client")
                fila.id_customer_supplier = n
                db.add(fila)
        base = {"full_name": "Ana", "email": "ana@x.com"}
        CustomerContactService.create({**base, "id_customer_supplier": 10}, user_id=1)
        b = CustomerContactService.create({**base, "id_customer_supplier": 20}, user_id=1)

        for malo in ({"full_name": "   "}, {"status": "banana"}):
            with self.subTest(malo=malo), self.assertRaises(AppError) as e:
                CustomerContactService.create(
                    {"full_name": "X", "id_customer_supplier": 10, **malo}, user_id=1)
            self.assertEqual(400, e.exception.status_code)
        with self.assertRaises(AppError) as e:
            CustomerContactService.update(b["id_customer_contact"], {"id_customer_supplier": 10}, user_id=1)
        self.assertEqual(409, e.exception.status_code)


if __name__ == "__main__":
    unittest.main()
