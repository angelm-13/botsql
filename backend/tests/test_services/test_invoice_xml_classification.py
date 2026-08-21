from __future__ import annotations

import unittest

from app.services.invoice_xml_classification import classify_invoice_direction


class TestInvoiceXmlClassification(unittest.TestCase):
    def test_principal_issuer_is_sale(self):
        self.assertEqual(
            classify_invoice_direction("AAA010101AAA", "aaa-010101-aaa", "XAXX010101000"),
            "venta",
        )

    def test_principal_receiver_is_purchase(self):
        self.assertEqual(
            classify_invoice_direction("AAA010101AAA", "SUP010101AAA", "AAA010101AAA"),
            "compra",
        )

    def test_unmatched_or_ambiguous_invoice_is_unclassified(self):
        self.assertEqual(
            classify_invoice_direction("AAA010101AAA", "SUP010101AAA", "CLI010101AAA"),
            "sin_clasificar",
        )
        self.assertEqual(
            classify_invoice_direction("AAA010101AAA", "AAA010101AAA", "AAA010101AAA"),
            "sin_clasificar",
        )


if __name__ == "__main__":
    unittest.main()