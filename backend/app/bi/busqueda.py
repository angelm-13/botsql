"""Busqueda global: "busca X" en cualquier dato de la base que el rol pueda leer.

Para una pregunta como "busca ACE133", "donde aparece BMW" o "todo sobre Roberto"
el modelo de lenguaje no hace falta ni conviene: el SQL se arma desde el esquema
YA FILTRADO del rol (`esquema`), asi que solo recorre tablas y columnas que esa
persona puede leer. El termino se limita a letras, numeros y unos signos, sin
comillas, por lo que no puede inyectar SQL; y la consulta pasa de todos modos por
el validador y el ejecutor de solo lectura como cualquier otra.

Por cada tabla se revisan sus columnas de texto, se traen hasta 3 coincidencias por
columna y se devuelven ordenadas por tabla: modulo, tabla, columna, valor y llave.
"""

from __future__ import annotations

import re
import unicodedata

_VERBOS = (r"busca(?:r|me)?|encuentra(?:me)?|encontrar|localiza(?:r)?|donde (?:aparece|aparecen|esta|estan|hay)|"
           r"todo (?:sobre|de|acerca de)|que (?:hay|sabes|tenemos) (?:de|sobre)|informacion (?:de|sobre)")
_BUSQUEDA = re.compile(
    r"^(?:" + _VERBOS + r")\s+(?:en (?:todo|toda la base|la base|el sistema)\s+)?(?:el |la |los |las |a )?"
    r"(?:texto |termino |palabra |registro |registros )?[\"']?(?P<t>[a-z0-9][a-z0-9 ._@-]{1,38}?)[\"']?$")

MAX_COLUMNAS = 400
POR_CONSULTA = 12
POR_COLUMNA = 3
MAX_FILAS = 60


def _norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip(" ?!.¿¡")


def detectar(pregunta: str) -> str | None:
    """El termino a buscar, saneado, o None si la pregunta no es una busqueda."""
    m = _BUSQUEDA.match(_norm(pregunta))
    if not m:
        return None
    t = re.sub(r"[^a-z0-9 ._@-]", "", m.group("t")).strip()
    return t if len(t) >= 3 else None


def _es_texto(tipo: str) -> bool:
    t = (tipo or "").upper()
    return any(k in t for k in ("CHAR", "TEXT", "VARCHAR", "CITEXT"))


def sentencias(esquema, termino: str) -> list[str]:
    """SQL de busqueda en bloques, armado solo con tablas/columnas permitidas."""
    # Defensa en profundidad: aunque `detectar` ya sanea, aqui se vuelve a limitar el
    # termino a letras, numeros y . _ @ - antes de que toque el SQL.
    termino = re.sub(r"[^a-zA-Z0-9 ._@-]", "", termino)
    patron = termino.replace("_", r"\_")
    ramas = []
    for r in esquema.relaciones:
        if r.es_vista:
            continue
        pk = next((c.nombre for c in r.columnas if c.es_pk), None)
        borrado = any(c.nombre.lower() == "deletion_date" for c in r.columnas)
        for c in r.columnas:
            if not _es_texto(c.tipo) or c.es_pk:
                continue
            id_ = f"CAST({pk} AS text)" if pk else "NULL"
            filtro = " AND deletion_date IS NULL" if borrado else ""
            ramas.append(
                f"(SELECT '{r.nombre}' AS tabla, '{c.nombre}' AS campo, CAST({c.nombre} AS text) AS valor, "
                f"{id_} AS llave FROM {r.nombre} WHERE {c.nombre} ILIKE '%{patron}%'{filtro} LIMIT {POR_COLUMNA})")
            if len(ramas) >= MAX_COLUMNAS:
                break
        if len(ramas) >= MAX_COLUMNAS:
            break
    bloques = []
    for i in range(0, len(ramas), POR_CONSULTA):
        bloques.append("SELECT tabla, campo, valor, llave FROM (" + " UNION ALL ".join(ramas[i:i + POR_CONSULTA]) + ") b")
    return bloques
