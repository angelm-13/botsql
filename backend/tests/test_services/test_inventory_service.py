from __future__ import annotations

import unittest

from app.services.inventory_service import _integer_quantity
from app.utils.errors import AppError


class TestInventoryServiceValidation(unittest.TestCase):
    def test_accepts_positive_integer_quantity(self):
        self.assertEqual(_integer_quantity("3"), 3)

    def test_rejects_zero_negative_boolean_and_fractional_quantity(self):
        for value in (0, -1, True, "1.5", None):
            with self.subTest(value=value), self.assertRaises(AppError):
                _integer_quantity(value)


if __name__ == "__main__":
    unittest.main()