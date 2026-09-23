"""Convierte un importe en pesos a su representacion en letras.

Requisito de la representacion impresa del CFDI ("Cantidad con letra"). Sin
libreria externa: los numeros a convertir siempre caben en el rango de una
factura real, y una dependencia mas para esto no se justifica.
"""

from __future__ import annotations


_UNIDADES = [
    "", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]
_DECENAS = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_CENTENAS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
    "seiscientos", "setecientos", "ochocientos", "novecientos",
]


def _centenas_a_letras(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cien"
    partes = []
    centena, resto = divmod(n, 100)
    if centena:
        partes.append(_CENTENAS[centena])
    if resto:
        if resto < 30:
            partes.append(_UNIDADES[resto])
        else:
            decena, unidad = divmod(resto, 10)
            partes.append(f"{_DECENAS[decena]} y {_UNIDADES[unidad]}" if unidad else _DECENAS[decena])
    return " ".join(partes)


def _apocope(texto: str) -> str:
    """"uno" -> "un", "veintiuno" -> "veintiún", antes de mil/millones."""
    if texto.endswith("veintiuno"):
        return texto[:-9] + "veintiún"
    if texto.endswith("uno"):
        return texto[:-3] + "un"
    return texto


def entero_a_letras(n: int) -> str:
    n = int(n)
    if n == 0:
        return "cero"
    partes = []
    millones, resto_millones = divmod(n, 1_000_000)
    miles, resto = divmod(resto_millones, 1000)
    if millones:
        partes.append("un millón" if millones == 1 else f"{_apocope(entero_a_letras(millones))} millones")
    if miles:
        partes.append("mil" if miles == 1 else f"{_apocope(_centenas_a_letras(miles))} mil")
    if resto:
        partes.append(_centenas_a_letras(resto))
    return " ".join(parte for parte in partes if parte)


def importe_a_letras(monto, moneda: str = "MXN") -> str:
    """3340.80 -> "Tres mil trescientos cuarenta pesos con ochenta centavos"."""
    try:
        monto = round(float(monto or 0), 2)
    except (TypeError, ValueError):
        monto = 0.0
    entero = int(monto)
    centavos = int(round((monto - entero) * 100))
    if centavos == 100:
        entero += 1
        centavos = 0
    unidad = "dólares" if str(moneda or "").upper() == "USD" else "pesos"
    texto = f"{entero_a_letras(entero)} {unidad} con {_centenas_a_letras(centavos) if centavos else 'cero'} centavos"
    return texto[0].upper() + texto[1:]
