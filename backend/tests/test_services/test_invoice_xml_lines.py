from decimal import Decimal
import unittest

from app.services.invoice_xml_lines import build_xml_line_payloads


class TestInvoiceXmlLines(unittest.TestCase):
    def test_maps_cfdi_concept_to_native_invoice_line(self):
        payload = build_xml_line_payloads(
            {'id_invoice': 7, 'id_customer_supplier': 9, 'id_status': 2},
            [{
                'description': 'Servicio de software', 'quantity': '2', 'unit_price': '40.00',
                'discount': '5.00', 'tax': '12.00', 'total': '87.00',
                'sat_product_key': '81111500', 'sat_unit_key': 'E48',
                'tax_object': '02', 'tax_rate': '0.160000',
            }],
            user_id=3,
        )[0]

        self.assertEqual(7, payload['id_invoice'])
        self.assertEqual(9, payload['id_customer_supplier'])
        self.assertEqual(3, payload['id_buyer'])
        self.assertEqual('authorized', payload['authorization_status'])
        self.assertEqual(Decimal('16.000000'), payload['tax_rate'])
        self.assertEqual('81111500', payload['sat_product_key'])

    def test_truncates_description_to_native_column_limit(self):
        payload = build_xml_line_payloads(
            {'id_invoice': 7, 'id_customer_supplier': 9, 'id_status': 2},
            [{'description': 'x' * 353}],
            user_id=3,
        )[0]

        self.assertEqual(200, len(payload['invoice_material_service_description']))