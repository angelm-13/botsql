from __future__ import annotations

import unittest

from app.services.manual_invoice_service import preview_manual_invoice


class TestManualInvoicePreview(unittest.TestCase):
    def test_calculates_iva_discounts_and_retentions(self):
        result = preview_manual_invoice({
            'iva_rate': '16',
            'isr_ret_rate': '1.25',
            'iva_ret_rate': '10.6667',
            'concepts': [{
                'description': 'Consultoria',
                'quantity': '2',
                'unit_price': '100',
                'discount': '20',
                'sat_product_key': '80101500',
                'sat_unit_key': 'E48',
            }],
        })

        self.assertTrue(result['can_create'])
        self.assertEqual(result['subtotal'], '200.00')
        self.assertEqual(result['discount'], '20.00')
        self.assertEqual(result['iva'], '28.80')
        self.assertEqual(result['isr_retention'], '2.25')
        self.assertEqual(result['iva_retention'], '19.20')
        self.assertEqual(result['total'], '187.35')

    def test_requires_sat_keys_before_creation(self):
        result = preview_manual_invoice({
            'concepts': [{'description': 'Servicio', 'quantity': 1, 'unit_price': 10}],
        })

        self.assertFalse(result['can_create'])
        self.assertIn('manual_invoice.concepts.0.sat_product_key_required', result['errors'])
        self.assertIn('manual_invoice.concepts.0.sat_unit_key_required', result['errors'])


if __name__ == '__main__':
    unittest.main()