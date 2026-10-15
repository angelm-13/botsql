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


if __name__ == "__main__":
    unittest.main()
