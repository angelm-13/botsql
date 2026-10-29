"""Ejemplos verificados para el modelo: "entrenamiento" sin ajustar pesos.

Dos fuentes, ambas de pares pregunta -> SQL que YA se ejecutaron contra la base de
tyakxa y devolvieron datos:

  * `ejemplos/verificados.jsonl`: generado por `scripts/bi_generar_ejemplos.py` a
    partir del esquema real (cientos de plantillas, todas probadas).
  * `BI_LEARN_PATH` (por omision `/uploads/bi/aprendido.jsonl`): consultas que el
    propio modelo resolvio bien en uso real -- sin error, sin reparacion y con
    filas --, guardadas para que la proxima pregunta parecida las use de modelo.

Por pregunta se recuperan los 3 mas parecidos (palabras en comun, con los mismos
recortes de plurales y sinonimos que `schema_linking`) y se muestran como ejemplos en
el prompt. Solo entran los que usan tablas que el rol del usuario puede leer.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from pathlib import Path

from .schema_linking import SINONIMOS, _raiz

BANCO = Path(__file__).with_name("ejemplos") / "verificados.jsonl"
RUTA_APRENDIDO = os.environ.get("BI_LEARN_PATH", "/uploads/bi/aprendido.jsonl")
TTL_S = 120
MAX_APRENDIDOS = 2000

_lock = threading.Lock()
_cache: tuple[float, list[dict]] | None = None


def _norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_VACIAS = {"los", "las", "una", "uno", "del", "por", "con", "que", "para", "hay", "dame", "muestrame", "lista",
           "total", "numero", "cuantos", "cuantas", "cual", "cuales", "sus", "mas"}


def _tokens(t: str) -> set:
    return {_raiz(p) for p in re.findall(r"[a-z0-9]{3,}", _norm(t)) if p not in _VACIAS}


def _leer(ruta) -> list[dict]:
    salida = []
    try:
        with open(ruta, encoding="utf-8") as fh:
            for linea in fh:
                try:
                    e = json.loads(linea)
                except ValueError:
                    continue
                if e.get("sql") and e.get("preguntas"):
                    salida.append(e)
    except OSError:
        pass
    return salida


def _indice() -> list[dict]:
    global _cache
    with _lock:
        if _cache and _cache[0] > time.time():
            return _cache[1]
    lista = _leer(BANCO) + _leer(RUTA_APRENDIDO)[-MAX_APRENDIDOS:]
    for e in lista:
        e["_tok"] = [_tokens(p) for p in e["preguntas"]]
    with _lock:
        globals()["_cache"] = (time.time() + TTL_S, lista)
    return lista


def _expandir(tokens: set) -> set:
    extra = set(tokens)
    for t in tokens:
        for clave, frags in SINONIMOS.items():
            if t == _raiz(clave):
                extra.update(_raiz(f) for f in frags)
    return extra


_CLAVES_DE_FORMA = {
    "mes": ("mes", "mensual", "evolucion"), "padre": ("tiene", "por", "top"), "ultimos": ("ultimo", "reciente"),
    "conteo": ("cuanto",), "suma": ("suma", "total"),
}


def buscar(pregunta: str, acceso=None, k: int = 3) -> list[dict]:
    q = _tokens(pregunta)
    if not q:
        return []
    qx = _expandir(q)
    forma = _norm(pregunta)
    puntuados = []
    for e in _indice():
        if acceso is not None and not acceso.es_admin and not all(acceso.permite_tabla(t) for t in e["tablas"]):
            continue
        mejor = 0
        # la tabla del ejemplo se nombra en la pregunta (producto/product, ticket...)
        de_tabla = {_raiz(p) for t in e["tablas"] for p in t.split("_") if len(p) >= 3}
        bonus_tabla = 4 if (qx & de_tabla) else 0
        for toks, variante in zip(e["_tok"], e["preguntas"]):
            directos = len(q & toks)
            if not directos:
                continue
            puntos = 3 * directos + len((qx - q) & toks) + (2 if e.get("tipo") == "conteo" and "cuant" in forma else 0)
            # la variante cubre la pregunta: premia que no sobren palabras
            puntos -= 0.5 * len(toks - qx)
            mejor = max(mejor, puntos + bonus_tabla)
        if mejor >= 3:
            puntuados.append((mejor + (1 if e.get("origen") == "aprendido" else 0) + (0.5 if e.get("filas") else 0), e))
    puntuados.sort(key=lambda x: -x[0])
    vistos, salida = set(), []
    for _, e in puntuados:
        if e["sql"] in vistos:
            continue
        vistos.add(e["sql"])
        salida.append(e)
        if len(salida) == k:
            break
    return salida


def formatear(ejemplos: list[dict], pregunta: str) -> str:
    """Bloque EJEMPLOS del prompt: la variante mas cercana a la pregunta + su SQL."""
    q = _tokens(pregunta)
    lineas = ["EJEMPLOS REALES de este esquema (copia el estilo y los nombres de columna exactos):"]
    for e in ejemplos:
        variante = max(e["preguntas"], key=lambda p: len(q & _tokens(p)))
        sql = e["sql"]
        if not re.search(r"\d|\b(top|mayor|menor|primer\w*|ultim\w*)\b", variante, re.I):
            # El LIMIT de un ejemplo sin "top N" se lo copiaria el modelo a preguntas que no lo piden.
            sql = re.sub(r"\s+LIMIT\s+\d+\s*$", "", sql, flags=re.I)
        lineas.append(f"P: {variante} -> {sql}")
    return "\n".join(lineas) + "\n\n"


def aprender(pregunta: str, sql: str, tablas: list[str], filas: int) -> None:
    """Guarda una consulta que el modelo resolvio bien, para usarla de ejemplo."""
    if not sql or filas <= 0 or not RUTA_APRENDIDO:
        return
    sql = " ".join(sql.split())
    try:
        previos = {e["sql"] for e in _leer(RUTA_APRENDIDO)}
        if sql in previos:
            return
        os.makedirs(os.path.dirname(RUTA_APRENDIDO), exist_ok=True)
        with open(RUTA_APRENDIDO, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"tipo": "aprendido", "origen": "aprendido", "tablas": sorted(set(tablas)),
                                 "preguntas": [pregunta.strip()[:200]], "sql": sql, "filas": filas},
                                ensure_ascii=False) + "\n")
        with _lock:
            globals()["_cache"] = None
    except OSError:
        pass
