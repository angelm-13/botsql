"""Lector de volcados MySQL/MariaDB, para importar el sistema anterior.

Por que un lector y no `psql -f`
--------------------------------
Los respaldos son de MySQL -comillas invertidas, `ENGINE=InnoDB`, `utf8mb3`, los
pragmas `/*!40101 ... */`- y el destino es PostgreSQL. No hay restauracion
directa que valga.

Y conviene que no la haya. Leyendo las filas se puede validar cada una contra las
reglas del almacen antes de escribirla, en lugar de meterla en crudo y descubrir
los descuadres despues. En estos respaldos eso importa mucho: `1990-01-01` no es
una fecha sino el centinela de "no aplica", y una restauracion literal habria
importado los 2 220 productos como borrados.

Los archivos no se modifican. Se abren en lectura y nada mas.

Que devuelve
------------
`leer(ruta)` da `{"tabla", "columnas", "filas"}`, donde cada fila es un dict con
None donde el volcado dice NULL. Los tipos se dejan como texto a proposito: la
conversion depende de la columna destino, y adivinarla aqui es donde se pierden
los ceros a la izquierda de un codigo.
"""

from __future__ import annotations

import pathlib
import re


# Los volcados de este sistema usan `1990-01-01 00:00:00` como "no aplica": se
# ve en que `producto.fecha_baja` tiene ese unico valor en las 2 220 filas.
# Tratarlo como fecha real es el error que importa los productos borrados y los
# vales cerrados.
CENTINELA_DE_FECHA = "1990-01-01 00:00:00"


def es_fecha_vacia(valor) -> bool:
    """Si esa fecha del volcado significa "no aplica"."""
    return valor in (None, "", CENTINELA_DE_FECHA)


def columnas_del_create(texto: str) -> tuple[str, list[str]]:
    """El nombre de la tabla y sus columnas, en el orden del CREATE TABLE.

    Se saca del DDL y no del INSERT porque estos volcados escriben
    `INSERT INTO tabla VALUES (...)` sin lista de columnas: el orden es el del
    CREATE, y sin leerlo no hay forma de saber que campo es cual.
    """
    m = re.search(r"CREATE TABLE `([^`]+)` \((.*?)\n\) ENGINE", texto, re.S)
    if not m:
        raise ValueError("no encuentro el CREATE TABLE en el volcado")
    tabla = m.group(1)
    columnas = []
    for linea in m.group(2).split("\n"):
        c = re.match(r"\s*`([^`]+)`\s", linea)
        if c:
            columnas.append(c.group(1))
    if not columnas:
        raise ValueError("el CREATE TABLE de `%s` no declara columnas" % tabla)
    return tabla, columnas


def _partir_tuplas(cuerpo: str) -> list[str]:
    """Corta el cuerpo de un VALUES en tuplas, respetando comillas y escapes.

    A mano y no con una expresion regular porque los textos traen parentesis,
    comas y comillas escapadas: una descripcion como
    `Taladro 1/2\\" Truper (rojo)` parte cualquier regla ingenua.
    """
    tuplas = []
    actual: list[str] = []
    dentro = False
    en_texto = False
    escapando = False

    for ch in cuerpo:
        if not dentro:
            if ch == "(":
                dentro = True
                actual = []
            continue

        if escapando:
            actual.append(ch)
            escapando = False
            continue

        if ch == "\\" and en_texto:
            escapando = True
            actual.append(ch)
            continue

        if ch == "'":
            en_texto = not en_texto
            actual.append(ch)
            continue

        if ch == ")" and not en_texto:
            tuplas.append("".join(actual))
            dentro = False
            continue

        actual.append(ch)

    return tuplas


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0"}


def _valores(tupla: str) -> list:
    """Los campos de una tupla, con None donde el volcado dice NULL."""
    campos = []
    actual: list[str] = []
    en_texto = False
    escapando = False

    for ch in tupla:
        if escapando:
            actual.append(_ESCAPES.get(ch, ch))
            escapando = False
            continue
        if ch == "\\" and en_texto:
            escapando = True
            continue
        if ch == "'":
            en_texto = not en_texto
            continue
        if ch == "," and not en_texto:
            campos.append("".join(actual))
            actual = []
            continue
        actual.append(ch)
    campos.append("".join(actual))

    # Un NULL sin comillas es nulo. Entre comillas seria el texto "NULL", y por
    # eso se compara el campo ya sin comillas contra el crudo recortado.
    return [None if c.strip() == "NULL" else c for c in campos]


def leer(ruta) -> dict:
    """Lee un archivo de volcado. No lo modifica: lo abre en lectura."""
    texto = pathlib.Path(ruta).read_text(encoding="utf-8", errors="replace")
    tabla, columnas = columnas_del_create(texto)

    filas = []
    patron = r"INSERT INTO `%s` VALUES\s*(.*?);\s*\n" % re.escape(tabla)
    for m in re.finditer(patron, texto, re.S):
        for tupla in _partir_tuplas(m.group(1)):
            valores = _valores(tupla)
            if len(valores) != len(columnas):
                # Se revienta en lugar de rellenar con nulos: una tupla con otro
                # numero de campos significa que este lector se equivoco, y
                # rellenar esconderia el error dentro de los datos importados.
                raise ValueError(
                    "%s: tupla con %d campos y la tabla declara %d -- %.120s"
                    % (tabla, len(valores), len(columnas), tupla))
            filas.append(dict(zip(columnas, valores)))

    return {"tabla": tabla, "columnas": columnas, "filas": filas}


def entero(valor):
    """El campo como entero, o None si no lo es."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return int(str(valor).strip())
    except ValueError:
        return None


def texto(valor, largo=None):
    """El campo como texto recortado, o None si viene vacio."""
    if valor is None:
        return None
    limpio = str(valor).strip()
    if not limpio:
        return None
    return limpio[:largo] if largo else limpio


def fecha(valor):
    """La fecha del volcado, o None si es nula o el centinela."""
    from datetime import datetime

    if es_fecha_vacia(valor):
        return None
    crudo = str(valor).strip()
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(crudo, formato)
        except ValueError:
            continue
    return None
