"""Politica de vacaciones de cada empresa y el saldo que sale de ella
(revision contable, 2026-10-28).

Cada año de servicio cumplido da un "bloque" de dias (LFT art. 76, o la tabla de
la empresa si da mas). La empresa decide, en Ajustes de nomina y con vigencia
como cualquier cifra:

* Como se ganan: por ley, el bloque completo al cumplir el año
  (`vacation_accrual_monthly` = 0); o mes a mes, la parte proporcional de cada
  mes completo del año que se esta trabajando (= 1: con 12 dias, 1 por mes; a
  medio año ya puede tomar 6).
* Adelantar: cuantos dias puede tomar de mas sobre lo ya ganado
  (`vacation_advance_max_days`; 0 = no se permite). Si se va de la empresa no
  se le descuenta nada (decision de RH, 2026-10-28; el descuento en el
  finiquito queda pendiente con la contadora).
* Plazo para usarlos: 12 o 18 meses despues del aniversario que completa el
  bloque (`vacation_expiry_months`). 18 = los 6 meses que da la ley para
  otorgarlas (art. 81) mas 1 año para reclamarlas (art. 516).
* Que pasa con lo no usado al vencer (`vacation_unused_policy`): 0 se pierde,
  1 pasa al año siguiente (no vence), 2 se paga en la nomina del periodo en que
  vence (concepto VAC_PAGADAS, grava ISR como sueldo).
* Avisos antes de que venza (`vacation_warning_days_1` y `_2`, en dias; 0 = sin
  aviso): al empleado y a su supervisor.

Sin capturar nada vale lo de siempre: bloque completo al aniversario, 12 meses,
se pierde, sin adelanto. Con eso el saldo da exactamente lo que daba antes.

Los dias tomados (aprobados y pendientes) se cargan al bloque mas viejo vigente
ese dia. Un dia sin bloque vigente con saldo es un adelanto: se carga al bloque
que se esta ganando y se "paga" conforme ese bloque se gana.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.services import payroll_tax_rules as ley

MENSUAL = "vacation_accrual_monthly"
ADELANTO = "vacation_advance_max_days"
PLAZO = "vacation_expiry_months"
NO_USADOS = "vacation_unused_policy"
AVISO_1, AVISO_2 = "vacation_warning_days_1", "vacation_warning_days_2"
SE_PIERDEN, SE_ACUMULAN, SE_PAGAN = 0, 1, 2

# clave -> (valor por omision, valores permitidos). Un rango (min, max) es de enteros.
POLITICA = {
    MENSUAL: (0, {0, 1}),
    ADELANTO: (0, range(0, 61)),
    PLAZO: (12, {12, 18}),
    NO_USADOS: (SE_PIERDEN, {SE_PIERDEN, SE_ACUMULAN, SE_PAGAN}),
    AVISO_1: (60, range(0, 366)),
    AVISO_2: (30, range(0, 366)),
}


def politica(db, al_dia: date) -> dict:
    """La politica vigente `al_dia`, con los valores por omision para lo no capturado."""
    from app.services.payroll_calculation_service import _vigentes
    capturados = _vigentes(db, tuple(POLITICA), al_dia)
    return {clave: int(capturados.get(clave, por_omision)) for clave, (por_omision, _) in POLITICA.items()}


def aniversario(ingreso: date, anios: int) -> date:
    try:
        return ingreso.replace(year=ingreso.year + anios)
    except ValueError:  # 29 de febrero en un año no bisiesto
        return date(ingreso.year + anios, 2, 28)


def _mas_meses(dia: date, meses: int) -> date:
    total = dia.month - 1 + meses
    anio, mes = dia.year + total // 12, total % 12 + 1
    return date(anio, mes, min(dia.day, calendar.monthrange(anio, mes)[1]))


def _meses_completos(desde: date, hasta: date) -> int:
    meses = (hasta.year - desde.year) * 12 + hasta.month - desde.month - (1 if hasta.day < desde.day else 0)
    return max(0, min(meses, 12))


@dataclass
class Bloque:
    """Los dias del año de servicio `anio`: se ganan entre `desde` y `completo`."""
    anio: int
    dias: int
    desde: date
    completo: date
    vence: date | None
    mensual: bool
    usados: int = field(default=0)

    def ganados(self, dia: date) -> int:
        if dia >= self.completo:
            return self.dias
        if not self.mensual or dia < self.desde:
            return 0
        return self.dias * _meses_completos(self.desde, dia) // 12

    def vigente(self, dia: date) -> bool:
        return self.vence is None or dia < self.vence


def bloques(ingreso: date, hasta: date, tabla: dict, pol: dict) -> list[Bloque]:
    """Los bloques que ya empezaron a ganarse `hasta` esa fecha (el ultimo, el del año en curso)."""
    salida, anio = [], 1
    while aniversario(ingreso, anio - 1) <= hasta:
        completo = aniversario(ingreso, anio)
        vence = None if pol[NO_USADOS] == SE_ACUMULAN else _mas_meses(completo, pol[PLAZO])
        salida.append(Bloque(anio=anio, dias=ley.dias_de_vacaciones(anio - 1, tabla),
                             desde=aniversario(ingreso, anio - 1), completo=completo, vence=vence,
                             mensual=bool(pol[MENSUAL])))
        anio += 1
    return salida


def _deuda(lista: list[Bloque], dia: date) -> int:
    """Dias adelantados que todavia no se ganan."""
    return sum(max(b.usados - b.ganados(dia), 0) for b in lista if b.vigente(dia))


def cargar(lista: list[Bloque], dias_tomados, maximo_adelanto: int) -> int:
    """Carga cada dia tomado (en orden) a su bloque. Devuelve cuantos dias no
    alcanzaron ni con el adelanto permitido."""
    sin_cubrir = 0
    for dia in sorted(dias_tomados):
        for b in lista:
            if b.vigente(dia) and b.ganados(dia) - b.usados > 0:
                b.usados += 1
                break
        else:
            # Adelanto: al bloque que se esta ganando ese dia (el primero vigente sin completar).
            destino = next((b for b in lista if b.vigente(dia) and dia < b.completo), None)
            if destino is None:
                sin_cubrir += 1
                continue
            destino.usados += 1
            if _deuda(lista, dia) > maximo_adelanto:
                sin_cubrir += 1
    return sin_cubrir


def resumen(lista: list[Bloque], al_dia: date, maximo_adelanto: int) -> dict:
    """Lo que el saldo muestra `al_dia`."""
    vigentes = [b for b in lista if b.vigente(al_dia)]
    ganados = sum(b.ganados(al_dia) for b in vigentes)
    disponibles = sum(b.ganados(al_dia) - b.usados for b in vigentes)
    deuda = _deuda(lista, al_dia)
    por_vencer = [{"service_year": b.anio, "days": b.ganados(al_dia) - b.usados, "expires_on": b.vence.isoformat()}
                  for b in vigentes if b.vence and b.ganados(al_dia) - b.usados > 0]
    return {"earned": ganados, "available": max(disponibles, 0), "advanced": deuda,
            "can_advance": max(maximo_adelanto - deuda, 0), "expiring": por_vencer}


def no_usados_que_vencen(lista: list[Bloque], desde: date, hasta: date) -> list[tuple[Bloque, int]]:
    """[(bloque, dias)] que vencen entre `desde` y `hasta` con dias sin usar
    (lo que se paga si la politica es SE_PAGAN). `lista` ya cargada."""
    return [(b, b.ganados(b.vence - timedelta(days=1)) - b.usados) for b in lista
            if b.vence and desde <= b.vence <= hasta and b.ganados(b.vence - timedelta(days=1)) - b.usados > 0]
