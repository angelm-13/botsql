"""Cifras oficiales 2026 para las pruebas de nomina (copia de lo que siembra
database/migrations/20261016130000_tablas_isr_y_parametros_de_nomina.sql).

En SQLite no corren las migraciones, asi que las pruebas las cargan con esto.
Solo las tarifas que usan las pruebas: diaria (1), quincenal (15) y mensual (30).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models import PayrollIsrBracket, PayrollParameter

TARIFAS_2026 = {
    1: [("0.01", "27.78", "0.00", "1.92"), ("27.79", "235.81", "0.53", "6.40"), ("235.82", "414.41", "13.85", "10.88"),
        ("414.42", "481.73", "33.28", "16.00"), ("481.74", "576.76", "44.05", "17.92"), ("576.77", "1163.25", "61.08", "21.36"),
        ("1163.26", "1833.44", "186.35", "23.52"), ("1833.45", "3500.35", "343.98", "30.00"), ("3500.36", "4667.13", "844.05", "32.00"),
        ("4667.14", "14001.38", "1217.42", "34.00"), ("14001.39", None, "4391.07", "35.00")],
    15: [("0.01", "416.70", "0.00", "1.92"), ("416.71", "3537.15", "7.95", "6.40"), ("3537.16", "6216.15", "207.75", "10.88"),
         ("6216.16", "7225.95", "499.20", "16.00"), ("7225.96", "8651.40", "660.75", "17.92"), ("8651.41", "17448.75", "916.20", "21.36"),
         ("17448.76", "27501.60", "2795.25", "23.52"), ("27501.61", "52505.25", "5159.70", "30.00"), ("52505.26", "70006.95", "12660.75", "32.00"),
         ("70006.96", "210020.70", "18261.30", "34.00"), ("210020.71", None, "65866.05", "35.00")],
    30: [("0.01", "844.59", "0.00", "1.92"), ("844.60", "7168.51", "16.22", "6.40"), ("7168.52", "12598.02", "420.95", "10.88"),
         ("12598.03", "14644.64", "1011.68", "16.00"), ("14644.65", "17533.64", "1339.14", "17.92"), ("17533.65", "35362.83", "1856.84", "21.36"),
         ("35362.84", "55736.68", "5665.16", "23.52"), ("55736.69", "106410.50", "10457.09", "30.00"), ("106410.51", "141880.66", "25659.23", "32.00"),
         ("141880.67", "425641.99", "37009.69", "34.00"), ("425642.00", None, "133488.54", "35.00")],
}

PARAMETROS_2026 = [
    ("uma_daily", "113.14", date(2025, 2, 1), date(2026, 1, 31)),
    ("uma_daily", "117.31", date(2026, 2, 1), date(2027, 1, 31)),
    ("uma_monthly", "3439.46", date(2025, 2, 1), date(2026, 1, 31)),
    ("uma_monthly", "3566.22", date(2026, 2, 1), date(2027, 1, 31)),
    ("minimum_wage_daily", "315.04", date(2026, 1, 1), date(2026, 12, 31)),
    ("subsidy_pct", "15.59", date(2026, 1, 1), date(2026, 1, 31)),
    ("subsidy_pct", "15.02", date(2026, 2, 1), date(2026, 12, 31)),
    ("subsidy_income_limit", "11492.66", date(2026, 1, 1), date(2026, 12, 31)),
    ("imss_em_surplus_pct", "0.400", date(2026, 1, 1), None),
    ("imss_em_cash_pct", "0.250", date(2026, 1, 1), None),
    ("imss_em_pensioners_pct", "0.375", date(2026, 1, 1), None),
    ("imss_iv_pct", "0.625", date(2026, 1, 1), None),
    ("imss_cv_pct", "1.125", date(2026, 1, 1), None),
    ("imss_surplus_umas", "3", date(2026, 1, 1), None),
    ("sbc_cap_umas", "25", date(2026, 1, 1), None),
    ("aguinaldo_days", "15", date(2026, 1, 1), None),
    ("vacation_premium_pct", "25", date(2026, 1, 1), None),
]


def sembrar_cifras_2026(db) -> None:
    for dias, tramos in TARIFAS_2026.items():
        for inferior, superior, cuota, pct in tramos:
            db.add(PayrollIsrBracket(period_days=dias, valid_year=2026, lower_limit=Decimal(inferior),
                                     upper_limit=Decimal(superior) if superior else None,
                                     fixed_fee=Decimal(cuota), rate_pct=Decimal(pct), created_by=1))
    for clave, valor, desde, hasta in PARAMETROS_2026:
        db.add(PayrollParameter(parameter_key=clave, value=Decimal(valor), valid_from=desde, valid_to=hasta, created_by=1))
