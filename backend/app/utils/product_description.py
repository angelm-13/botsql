"""Como se escribe la descripcion de un producto: formato de oracion.

La regla, tal como la pidio Adser: la primera letra va en mayuscula, el resto en
minusculas, con espacios, numeros y simbolos como la diagonal y el guion (para
las fracciones: 3/4). Ejemplo: "Pulidor chico 3/4".

Las SIGLAS se respetan: una palabra de dos o mas letras toda en mayusculas
("PVC", "LED", "RJ45") no se baja a minusculas. Hay un matiz, porque el sistema
anterior guardo casi todo en MAYUSCULAS: en un texto que esta COMPLETO en
mayusculas ("PULIDOR CHICO 3/4") no se puede distinguir una sigla de una palabra
escrita con la tecla bloqueada, asi que ahi solo se conservan las siglas
conocidas (ACRONIMOS_CONOCIDOS). En un texto con minusculas, cualquier palabra
toda en mayusculas se toma por sigla.

Hay UNA sola definicion de "valido": un texto es valido cuando sugerir() no lo
cambia. Asi la validacion y la sugerencia no pueden contradecirse. El frontend
tiene el mismo algoritmo en `src/utils/productDescription.js`; si cambia uno,
cambia el otro.
"""
from __future__ import annotations

import re

# Siglas que se conservan aun cuando todo el texto viene en mayusculas.
ACRONIMOS_CONOCIDOS = frozenset({
    "PVC", "CPVC", "ABS", "LED", "USB", "HDMI", "HSS", "NPT", "AWG", "MDF", "OSB",
    "EPDM", "CFE", "IVA", "SDS", "RJ45", "UTP", "LCD", "GPS", "RPM", "PPR", "TIG",
    "MIG", "AC", "DC", "NOM", "SAE", "ISO", "EPP", "IP", "PU", "PP", "PE",
})

MAX_LONGITUD = 250

_CARACTERES_PERMITIDOS = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 /\-.,()"°%#+&:]+$')
_LETRAS = re.compile(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]')
# Un codigo de modelo mezcla letras y numeros con una letra antes y otra despues
# de un numero (B26T600). "18KG" no lo es: ahi no hay letra antes del numero.
_CODIGO_DE_MODELO = re.compile(r'^[A-Z0-9\-]*[A-Z]\d+[A-Z][A-Z0-9\-]*$')
# Una letra suelta es una forma o un tipo ("prensa C", "perfil T"), no una
# palabra; salvo las que en espanol SON palabras (a, y, o, e, u).
_LETRAS_QUE_SON_PALABRA = frozenset("AYOEU")


def _es_sigla_con_forma(palabra: str) -> bool:
    """Dos o mas letras, todas mayusculas (puede llevar digitos: RJ45)."""
    letras = _LETRAS.findall(palabra)
    return len(letras) >= 2 and all(c == c.upper() for c in letras)


def _se_conserva_en_mayusculas(nucleo: str) -> bool:
    if _CODIGO_DE_MODELO.match(nucleo):
        return True
    return (len(nucleo) == 1 and nucleo.isalpha() and nucleo.isupper()
            and nucleo not in _LETRAS_QUE_SON_PALABRA)


def sugerir(texto: str | None) -> str:
    """El texto en formato de oracion, respetando las siglas."""
    limpio = " ".join(str(texto or "").split())
    if not limpio:
        return ""
    todo_en_mayusculas = not any(c.islower() for c in limpio)

    palabras = []
    for palabra in limpio.split(" "):
        nucleo = palabra.strip('.,()"')
        if _es_sigla_con_forma(nucleo) and (
            not todo_en_mayusculas or nucleo in ACRONIMOS_CONOCIDOS
        ):
            palabras.append(palabra)
        elif _se_conserva_en_mayusculas(nucleo):
            palabras.append(palabra)
        else:
            palabras.append(palabra.lower())

    primera = palabras[0]
    # La primera letra del texto va en mayuscula, sea cual sea la palabra.
    for i, c in enumerate(primera):
        if c.isalpha():
            primera = primera[:i] + c.upper() + primera[i + 1:]
            break
    palabras[0] = primera
    return " ".join(palabras)


def es_valida(texto: str | None) -> bool:
    """Vacia se acepta: la descripcion no es obligatoria. Lo escrito, debe cumplir."""
    if texto is None or str(texto).strip() == "":
        return True
    texto = str(texto)
    if len(texto) > MAX_LONGITUD:
        return False
    if not _CARACTERES_PERMITIDOS.match(texto):
        return False
    if not _LETRAS.search(texto[:1]) or not texto[:1].isupper():
        return False
    return sugerir(texto) == texto
