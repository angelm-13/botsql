"""Reglas de ley de la nomina: ISR, subsidio para el empleo e IMSS (cuota obrera).

Las CIFRAS (tarifas, UMA, salario minimo, porcentajes) no viven aqui: estan en
`payroll_isr_bracket` y `payroll_parameter`, con su vigencia y su fuente, para
que RH o el contador las actualicen cada año sin programar. Aqui solo estan las
REGLAS, que cambian solo si cambia la ley:

ISR (art. 96 LISR, art. 175 RLISR, regla 3.12.2 RMF)
    Se busca el tramo de la tarifa donde cae la base gravable del periodo:
    ISR = cuota fija + (base - limite inferior) x porcentaje.
    Tabla segun los dias del periodo: 7, 10, 15 (14 a 16 dias) o mensual (28 a
    31); cualquier otro largo usa la tarifa diaria multiplicada por los dias.

Subsidio para el empleo (decreto, DOF 31/12/2025)
    Aplica si el ingreso gravable, llevado a mes (/ dias x 30.4), no pasa del
    limite. Monto: UMA mensual x porcentaje; en periodos menores a un mes se
    divide entre 30.4 y se multiplica por los dias. Se resta del ISR y nunca lo
    vuelve negativo (desde 2024 ya no hay subsidio "a favor" en efectivo).

IMSS, cuota del trabajador (Ley del Seguro Social)
    Salario base de cotizacion (SBC) = salario diario x factor de integracion,
    con piso en el salario minimo y tope de 25 UMA (art. 28).
    Factor = 1 + (dias de aguinaldo + dias de vacaciones x prima vacacional) / 365
    (LFT arts. 76, 80 y 87). Las vacaciones dependen de la antiguedad (art. 76,
    reforma 2023: 12 dias el primer año).
    Cuota por dia = SBC x (prestaciones en dinero + gastos medicos de
    pensionados + invalidez y vida + cesantia y vejez) + (SBC - 3 UMA, si es
    positivo) x excedente. Quien gana el salario minimo no paga cuota obrera: la
    cubre el patron (art. 36).

Aguinaldo (LFT art. 87)
    Salario diario x dias de aguinaldo x (dias del año desde el ingreso, o
    desde el 1 de enero, hasta el 31 de diciembre / dias del año). Las faltas
    no lo reducen.

Prima vacacional (LFT art. 80)
    Se paga al cumplir cada año de servicio: dias de vacaciones del año que se
    cumplio x salario diario x porcentaje de prima.

Exencion del ISR (LISR art. 93 fr. XIV)
    El aguinaldo esta exento hasta 30 UMA y la prima vacacional hasta 15; solo
    lo que pase del tope se suma a la base gravable del periodo. No pagan cuota
    extra del IMSS: ya estan dentro del factor de integracion.

Fuera de alcance: integrar al SBC las percepciones variables, INFONAVIT, la
cuota patronal, el ajuste anual del ISR y el calculo opcional del ISR del
aguinaldo del art. 174 RLISR.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")
DIAS_MES = Decimal("30.4")


def dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def tabla_para_dias(dias: int) -> tuple[int, Decimal]:
    """(tabla oficial a usar, factor por el que se multiplica)."""
    if dias == 7:
        return 7, Decimal(1)
    if dias == 10:
        return 10, Decimal(1)
    if 14 <= dias <= 16:
        return 15, Decimal(1)
    if 28 <= dias <= 31:
        return 30, Decimal(1)
    return 1, Decimal(dias)


def isr_por_tarifa(base, tramos, factor=Decimal(1)) -> Decimal:
    """ISR de `base` con la tarifa `tramos` [(inferior, superior|None, cuota, pct)].

    `factor` escala la tarifa (la diaria x dias del periodo).
    """
    base = Decimal(str(base or 0))
    if base <= 0:
        return dinero(0)
    for inferior, superior, cuota, pct in sorted(tramos, key=lambda t: Decimal(str(t[0]))):
        inferior = Decimal(str(inferior)) * factor
        tope = None if superior is None else Decimal(str(superior)) * factor
        if base >= inferior and (tope is None or base <= tope):
            return dinero(Decimal(str(cuota)) * factor + (base - inferior) * Decimal(str(pct)) / 100)
    # Entre dos tramos escalados puede quedar un centavo de hueco: el ultimo
    # tramo cuyo limite inferior ya se paso es el que aplica.
    aplicables = [t for t in tramos if base >= Decimal(str(t[0])) * factor]
    inferior, _, cuota, pct = max(aplicables, key=lambda t: Decimal(str(t[0])))
    inferior = Decimal(str(inferior)) * factor
    return dinero(Decimal(str(cuota)) * factor + (base - inferior) * Decimal(str(pct)) / 100)


def subsidio_para_el_empleo(base_gravable, dias: int, uma_mensual, porcentaje, limite_mensual) -> Decimal:
    """Subsidio del periodo; 0 si el ingreso llevado a mes pasa del limite."""
    base = Decimal(str(base_gravable or 0))
    if base <= 0 or dias <= 0:
        return dinero(0)
    mensual = Decimal(str(uma_mensual)) * Decimal(str(porcentaje)) / 100
    if 28 <= dias <= 31:
        ingreso_mensual, monto = base, mensual
    else:
        ingreso_mensual = base / dias * DIAS_MES
        monto = mensual / DIAS_MES * dias
    if ingreso_mensual > Decimal(str(limite_mensual)):
        return dinero(0)
    return dinero(monto)


def dias_de_vacaciones(anios_cumplidos: int) -> int:
    """Vacaciones del año de servicio en curso (LFT art. 76, reforma 2023)."""
    anio = max(0, int(anios_cumplidos)) + 1
    if anio <= 5:
        return 10 + 2 * anio          # 12, 14, 16, 18, 20
    return 20 + 2 * ((anio - 1) // 5)  # 6-10: 22, 11-15: 24, 16-20: 26, ...


def anios_cumplidos(ingreso: date | None, al_dia: date) -> int:
    if not ingreso or ingreso > al_dia:
        return 0
    anios = al_dia.year - ingreso.year
    if (al_dia.month, al_dia.day) < (ingreso.month, ingreso.day):
        anios -= 1
    return max(0, anios)


def factor_de_integracion(dias_aguinaldo, dias_vacaciones, prima_vacacional_pct) -> Decimal:
    prestaciones = Decimal(str(dias_aguinaldo)) + Decimal(str(dias_vacaciones)) * Decimal(str(prima_vacacional_pct)) / 100
    return (1 + prestaciones / 365).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def salario_base_de_cotizacion(salario_diario, factor, salario_minimo, uma_diaria, tope_umas) -> Decimal:
    sbc = Decimal(str(salario_diario)) * Decimal(str(factor))
    sbc = max(sbc, Decimal(str(salario_minimo)))
    return dinero(min(sbc, Decimal(str(uma_diaria)) * Decimal(str(tope_umas))))


def cuota_obrera_imss(sbc, dias, salario_diario, salario_minimo, uma_diaria, p: dict) -> Decimal:
    """Cuota del trabajador por `dias` cotizados. `p`: porcentajes y umbral (ver parametros)."""
    if dias <= 0 or Decimal(str(salario_diario)) <= Decimal(str(salario_minimo)):
        return dinero(0)
    sbc = Decimal(str(sbc))
    sobre_sbc = sum(Decimal(str(p[k])) for k in
                    ("imss_em_cash_pct", "imss_em_pensioners_pct", "imss_iv_pct", "imss_cv_pct")) / 100
    excedente = max(sbc - Decimal(str(p["imss_surplus_umas"])) * Decimal(str(uma_diaria)), Decimal(0))
    por_dia = sbc * sobre_sbc + excedente * Decimal(str(p["imss_em_surplus_pct"])) / 100
    return dinero(por_dia * dias)


def aguinaldo(salario_diario, dias_aguinaldo, ingreso: date | None, anio: int) -> Decimal:
    """Aguinaldo del `anio`, proporcional si entro ese mismo año. Sin fecha de
    ingreso se paga completo (el calculo lo avisa aparte)."""
    inicio, fin = date(anio, 1, 1), date(anio, 12, 31)
    if ingreso and ingreso > fin:
        return dinero(0)
    desde = max(ingreso, inicio) if ingreso else inicio
    dias_del_anio = (fin - inicio).days + 1
    trabajados = (fin - desde).days + 1
    return dinero(Decimal(str(salario_diario)) * Decimal(str(dias_aguinaldo)) * trabajados / dias_del_anio)


def aniversario_en(ingreso: date | None, inicio: date, fin: date) -> date | None:
    """El aniversario de ingreso que cae entre `inicio` y `fin` (sin contar el
    propio dia de ingreso). Quien entro un 29 de febrero cumple el 28 en años
    no bisiestos."""
    if not ingreso:
        return None
    for anio in range(inicio.year, fin.year + 1):
        try:
            dia = date(anio, ingreso.month, ingreso.day)
        except ValueError:
            dia = date(anio, 2, 28)
        if dia > ingreso and inicio <= dia <= fin:
            return dia
    return None


def prima_vacacional(salario_diario, anios_de_servicio: int, prima_pct) -> tuple[int, Decimal]:
    """(dias de vacaciones del año cumplido, prima) al cumplir `anios_de_servicio`."""
    if anios_de_servicio < 1:
        return 0, dinero(0)
    dias = dias_de_vacaciones(anios_de_servicio - 1)
    return dias, dinero(Decimal(str(salario_diario)) * dias * Decimal(str(prima_pct)) / 100)


def parte_gravada(monto, uma_diaria, umas_exentas) -> Decimal:
    """Lo que pasa del tope exento (art. 93 fr. XIV LISR)."""
    exento = Decimal(str(uma_diaria)) * Decimal(str(umas_exentas))
    return dinero(max(Decimal(str(monto or 0)) - exento, Decimal(0)))
