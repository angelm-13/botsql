from __future__ import annotations

import unittest
from decimal import Decimal

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


def test_preview_rejects_an_iva_rate_outside_the_sat_catalog():
    """El SAT solo acepta traslado de IVA al 0%, 8% o 16%."""
    concepts = [{
        "description": "Servicio", "quantity": 1, "unit_price": 100,
        "sat_product_key": "81111500", "sat_unit_key": "E48",
    }]
    result = preview_manual_invoice({"concepts": concepts, "iva_rate": "15"})

    assert result["can_create"] is False
    assert "manual_invoice.concepts.0.iva_rate_not_in_catalog" in result["errors"]

    for rate in ("0", "8", "16"):
        assert preview_manual_invoice({"concepts": concepts, "iva_rate": rate})["can_create"] is True


def test_preview_rounds_each_line_before_adding_up():
    """SubTotal debe ser la suma de los Importe ya redondeados de cada partida."""
    result = preview_manual_invoice({"concepts": [
        {"description": "A", "quantity": 3, "unit_price": "33.333",
         "sat_product_key": "81111500", "sat_unit_key": "E48"},
        {"description": "B", "quantity": 7, "unit_price": "1.115",
         "sat_product_key": "81111500", "sat_unit_key": "E48"},
    ]})

    amounts = [Decimal(concept["amount"]) for concept in result["concepts"]]
    assert amounts == [Decimal("100.00"), Decimal("7.81")]
    assert Decimal(result["subtotal"]) == sum(amounts)
    assert Decimal(result["iva"]) == sum(Decimal(item["iva"]) for item in result["concepts"])


def test_preview_distinguishes_exempt_from_zero_rate():
    concepts = [{
        "description": "Alimento", "quantity": 1, "unit_price": 100,
        "sat_product_key": "50192700", "sat_unit_key": "H87",
    }]
    exempt = preview_manual_invoice({"concepts": concepts, "iva_tipo": "exento"})["concepts"][0]
    zero_rate = preview_manual_invoice({"concepts": concepts, "iva_tipo": "0"})["concepts"][0]

    assert exempt["iva_exempt"] is True
    assert zero_rate["iva_exempt"] is False
    # Ambos suman cero de IVA, pero se declaran distinto en el CFDI.
    assert exempt["iva"] == zero_rate["iva"] == "0.00"
    assert exempt["tax_object"] == zero_rate["tax_object"] == "02"


def test_preview_marks_non_taxable_concepts_without_breakdown():
    result = preview_manual_invoice({"iva_tipo": "sin_iva", "concepts": [{
        "description": "No objeto", "quantity": 1, "unit_price": 100,
        "sat_product_key": "44121600", "sat_unit_key": "H87",
    }]})
    concept = result["concepts"][0]

    assert concept["tax_object"] == "01"
    assert concept["iva"] == "0.00"
    assert result["total"] == "100.00"


def test_preview_rejects_non_finite_amounts_and_a_negative_total():
    """NaN/Infinity daban 500; retenciones al 100% dejaban un total negativo."""
    import pytest
    from app.utils.errors import AppError

    concept = {"description": "S", "quantity": 1, "unit_price": 1000,
               "sat_product_key": "81111500", "sat_unit_key": "E48"}
    for campo, valor in (("quantity", "NaN"), ("unit_price", "Infinity")):
        with pytest.raises(AppError) as e:
            preview_manual_invoice({"concepts": [{**concept, campo: valor}]})
        assert e.value.status_code == 400

    negativo = preview_manual_invoice({
        "concepts": [concept], "iva_rate": "16", "isr_ret_rate": "100", "iva_ret_rate": "100"})
    assert negativo["can_create"] is False
    assert "manual_invoice.total_negative" in negativo["errors"]

    from app.services.manual_invoice_service import _tipo_de_cambio_por_omision
    with pytest.raises(AppError):
        _tipo_de_cambio_por_omision({"currency": "USD", "type_exchange_rate": "-5"})
