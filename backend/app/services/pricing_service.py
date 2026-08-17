from __future__ import annotations
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class PricingService:
    """Centraliza calculo de precio publico para catalogo web.

    No modifica product. Consume gross_price, margin_percent y manual_price.
    """

    @staticmethod
    def _decimal(value, default='0') -> Decimal:
        if value in (None, ''):
            value = default
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(str(default))

    @classmethod
    def iva_rate(cls) -> Decimal:
        return cls._decimal(os.getenv('IVA_RATE', '0.16'), '0.16')

    @classmethod
    def calculate_public_price(cls, *, base_price, margin_percent=None, manual_price=None) -> dict:
        base = cls._decimal(base_price)
        margin = cls._decimal(margin_percent)
        manual = None if manual_price in (None, '') else cls._decimal(manual_price)

        if manual is not None:
            subtotal = manual
            source = 'manual_price'
        else:
            subtotal = base * (Decimal('1') + (margin / Decimal('100')))
            source = 'margin_percent'

        iva = cls.iva_rate()
        tax_amount = subtotal * iva
        total = subtotal + tax_amount
        q = Decimal('0.01')

        return {
            'base_price': float(base.quantize(q, rounding=ROUND_HALF_UP)),
            'margin_percent': float(margin.quantize(q, rounding=ROUND_HALF_UP)),
            'manual_price': None if manual is None else float(manual.quantize(q, rounding=ROUND_HALF_UP)),
            'subtotal': float(subtotal.quantize(q, rounding=ROUND_HALF_UP)),
            'tax_rate': float(iva.quantize(q, rounding=ROUND_HALF_UP)),
            'tax_amount': float(tax_amount.quantize(q, rounding=ROUND_HALF_UP)),
            'public_price': float(total.quantize(q, rounding=ROUND_HALF_UP)),
            'price_source': source,
        }
