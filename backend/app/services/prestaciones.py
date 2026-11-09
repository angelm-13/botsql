"""Prestaciones que cada empresa activa (respuestas de RH, 2026-11-04: "no todas lo ofrecen").

Cada una es un concepto de nomina (descuento) con codigo propio `PR_...` (para no
esconder un concepto que la empresa ya hubiera creado con su nombre) que existe siempre en el catalogo
(migracion 20261105100000) pero solo se ofrece en la hoja de nomina si la empresa
la activa en Cifras oficiales, pestaña "Opciones de calculo" (1 = si, 0 = no;
sin capturar, no). Son descuentos que no cambian la base del ISR ni del IMSS.

Los vales de despensa quedan fuera hasta que la contadora confirme como gravan.
"""
from __future__ import annotations

# codigo del concepto -> clave de la opcion en payroll_parameter
PRESTACIONES = {
    "PR_INFONAVIT": "benefit_infonavit",
    "PR_FONACOT": "benefit_fonacot",
    "PR_CAJA_AHORRO": "benefit_savings_fund",
    "PR_PRESTAMO": "benefit_loan",
    "PR_PENSION_ALIM": "benefit_alimony",
}
# clave -> (valor por omision, valores permitidos), como las demas politicas.
POLITICA_DE_PRESTACIONES = {clave: (0, range(0, 2)) for clave in PRESTACIONES.values()}


def activas(db, al_dia) -> set[str]:
    """Codigos de las prestaciones que la empresa tiene activas al dia."""
    from app.services.payroll_calculation_service import _vigentes
    capturados = _vigentes(db, tuple(POLITICA_DE_PRESTACIONES), al_dia)
    return {codigo for codigo, clave in PRESTACIONES.items() if int(capturados.get(clave, 0) or 0) == 1}
