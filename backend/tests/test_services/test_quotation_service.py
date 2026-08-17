from __future__ import annotations

import unittest
from decimal import Decimal

from app.services.quotation_service import calculate_totals, validate_transition
from app.utils.errors import AppError


class TestQuotationService(unittest.TestCase):
    def test_calculates_decimal_totals_with_discount(self):
        result = calculate_totals(
            [{"quantity": "3", "gross_price": "0.10", "discount": "0.05"}],
            "16",
        )

        self.assertEqual(result["subtotal"], Decimal("0.30"))
        self.assertEqual(result["tax"], Decimal("0.04"))
        self.assertEqual(result["total"], Decimal("0.29"))

    def test_allows_only_explicit_lifecycle_transitions(self):
        self.assertEqual(validate_transition("cotizacion", "sent"), "sent")
        self.assertEqual(validate_transition("sent", "approved"), "approved")
        with self.assertRaises(AppError):
            validate_transition("draft", "converted")

    def test_rejects_invalid_line_values(self):
        with self.assertRaises(AppError):
            calculate_totals([{"quantity": 0, "gross_price": 10}], 16)
        with self.assertRaises(AppError):
            calculate_totals([{"quantity": 1, "gross_price": 10, "discount": 11}], 16)


if __name__ == "__main__":
    unittest.main()