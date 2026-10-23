"""Seleccion de tablas por pregunta (schema linking).

La base tiene ~150 tablas: no caben en el prompt de un modelo chico, y
truncar por orden alfabetico dejaba fuera la mayoria. Aqui el catalogo
completo sigue siendo consultable (el validador de seguridad ve todo), pero
al modelo solo se le muestra el DDL de las tablas relevantes a la pregunta,
mas las vecinas por llave foranea y un indice con el nombre de las demas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

MAX_TABLAS_PROMPT = 6       # tablas con DDL completo, antes de vecinas
MAX_VECINAS = 3

# Vocabulario de negocio (espanol) -> fragmentos de nombre de tabla/columna.
SINONIMOS: dict[str, tuple[str, ...]] = {
    "factura": ("invoice", "cfdi", "fiscal", "stamp"),
    "cobro": ("invoice", "payment", "receivable"),
    "pago": ("payment", "invoice", "payroll"),
    "abono": ("payment",),
    "incidencia": ("incident",),
    "vale": ("incident", "nm_incident"),
    "herramienta": ("product", "nm_incident"),
    "incidente": ("incident",),
    "producto": ("product", "material"),
    "articulo": ("product", "material"),
    "cliente": ("customer", "supplier"),
    "proveedor": ("supplier", "customer"),
    "contacto": ("contact", "customer"),
    "usuario": ("user",),
    "empleado": ("user", "payroll", "waiter", "operator"),
    "nomina": ("payroll",),
    "sueldo": ("payroll",),
    "salario": ("payroll",),
    "venta": ("sale", "pos", "order", "quotation"),
    "compra": ("purchase", "order"),
    "gasto": ("expense",),
    "inventario": ("inventory", "stock", "lot"),
    "existencia": ("stock", "inventory"),
    "almacen": ("warehouse", "stock", "inventory"),
    "banco": ("bank",),
    "cuenta": ("account", "bank"),
    "estado": ("status", "statement"),
    "departamento": ("department",),
    "proyecto": ("proyect",),
    "tarea": ("task",),
    "ticket": ("ticket",),
    "encuesta": ("survey",),
    "equipo": ("team", "equipment"),
    "cita": ("appointment",),
    "reservacion": ("reservation",),
    "reserva": ("reservation",),
    "mesa": ("table",),
    "platillo": ("dish", "recipe"),
    "cocina": ("dish", "recipe", "order"),
    "mesero": ("waiter",),
    "caja": ("cash",),
    "viaje": ("trip", "shipment"),
    "envio": ("shipment",),
    "transporte": ("trip", "unit", "trailer", "operator"),
    "unidad": ("unit",),
    "remolque": ("trailer",),
    "operador": ("operator",),
    "laboratorio": ("laboratory",),
    "documento": ("document",),
    "kpi": ("kpi",),
    "indicador": ("kpi",),
    "cotizacion": ("quotation",),
    "promocion": ("promotion",),
    "lealtad": ("loyalty",),
    "credito": ("credit",),
    "marca": ("brand",),
    "familia": ("family",),
    "categoria": ("category", "type"),
    "servicio": ("service",),
    "mantenimiento": ("maintenance",),
    "contrato": ("contract",),
    "tarifa": ("rate",),
    "sucursal": ("branch",),
    "ubicacion": ("location",),
    "notificacion": ("notification",),
    "bitacora": ("log", "supervisor"),
    "supervisor": ("supervisor",),
    "movimiento": ("movement", "ledger"),
    "cancelacion": ("cancellation",),
}

_PALABRAS_VACIAS = {
    "los", "las", "una", "uno", "unos", "unas", "del", "por", "con", "que",
    "para", "cual", "cuales", "como", "cuantos", "cuantas", "dame", "muestra",
    "muestrame", "lista", "listar", "total", "todos", "todas", "mas", "menos",
    "entre", "desde", "hasta", "este", "esta", "esos", "mes", "anio", "dia",
}


def _norm(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin if not unicodedata.combining(c))


def _raiz(palabra: str) -> str:
    for sufijo in ("ciones", "cion", "es", "s"):
        if palabra.endswith(sufijo) and len(palabra) - len(sufijo) >= 4:
            return palabra[: -len(sufijo)]
    return palabra


def _tokens_pregunta(pregunta: str) -> set[str]:
    crudas = re.findall(r"[a-z0-9]{3,}", _norm(pregunta))
    return {_raiz(p) for p in crudas if p not in _PALABRAS_VACIAS}


def _coincide(a: str, b: str) -> bool:
    return a == b or (len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)))


def _puntaje(relacion, tokens: set[str], expandidos: set[str]) -> int:
    nombre = [_raiz(t) for t in relacion.nombre.lower().split("_") if t]
    puntos = 0
    for t in nombre:
        if any(_coincide(t, q) for q in tokens):
            puntos += 4
        elif any(_coincide(t, q) for q in expandidos):
            puntos += 3
    for col in relacion.columnas:
        for t in (_raiz(x) for x in col.nombre.lower().split("_") if x):
            if len(t) >= 4 and any(_coincide(t, q) for q in tokens):
                puntos += 1
    return puntos


def _destino_fk(fk: str | None, por_nombre: dict) -> str | None:
    if not fk:
        return None
    partes = fk.replace('"', "").split(".")
    for candidato in (partes[-2] if len(partes) >= 2 else None, partes[0]):
        if candidato and candidato.lower() in por_nombre:
            return candidato.lower()
    return None


def relaciones_para_pregunta(esquema, pregunta: str):
    """Devuelve (relaciones con DDL completo, nombres del resto)."""
    relaciones = list(esquema.relaciones)
    if len(relaciones) <= MAX_TABLAS_PROMPT + MAX_VECINAS:
        return relaciones, []

    tokens = _tokens_pregunta(pregunta)
    expandidos: set[str] = set()
    for t in tokens:
        for clave, frags in SINONIMOS.items():
            if _coincide(t, _raiz(clave)):
                expandidos.update(_raiz(f) for f in frags)

    por_nombre = {r.nombre.lower(): r for r in relaciones}
    entrantes: dict[str, int] = {n: 0 for n in por_nombre}
    for r in relaciones:
        for c in r.columnas:
            d = _destino_fk(c.fk, por_nombre)
            if d and d != r.nombre.lower():
                entrantes[d] += 1

    puntajes = {r.nombre.lower(): _puntaje(r, tokens, expandidos) for r in relaciones}
    ranking = sorted(relaciones, key=lambda r: (-puntajes[r.nombre.lower()],
                                                -entrantes[r.nombre.lower()], r.nombre))
    elegidas = [r for r in ranking if puntajes[r.nombre.lower()] > 0][:MAX_TABLAS_PROMPT]
    if not elegidas:   # pregunta sin pistas: las tablas mas referenciadas
        elegidas = sorted(relaciones, key=lambda r: (-entrantes[r.nombre.lower()], r.nombre))[:MAX_TABLAS_PROMPT]

    nombres = {r.nombre.lower() for r in elegidas}
    vecinas: list = []
    for r in list(elegidas):
        for c in r.columnas:
            d = _destino_fk(c.fk, por_nombre)
            if d and d not in nombres and len(vecinas) < MAX_VECINAS:
                nombres.add(d)
                vecinas.append(por_nombre[d])
    finales = elegidas + vecinas
    resto = sorted(r.nombre for r in relaciones if r.nombre.lower() not in nombres)
    return finales, resto


# Columnas de bitacora que tiene casi cada tabla: ocupan una cuarta parte del
# DDL y casi nunca sirven para contestar. Se quitan SOLO del prompt (el
# validador sigue conociendolas). Cada token del prompt son segundos en CPU.
_RUIDO = {"created_by", "creation_date", "last_update_date", "ajustado_por_gestor", "updated_by"}
_NOTA_BORRADO = "-- Filas dadas de baja tienen deletion_date NO nulo: filtra deletion_date IS NULL.\n"


def _sin_ruido(relaciones):
    salida = []
    for r in relaciones:
        cols = tuple(c for c in r.columnas if c.nombre.lower() not in _RUIDO) or r.columnas
        salida.append(replace(r, columnas=cols))
    return tuple(salida)


_TIPOS_CORTOS = (("INT", "int"), ("SERIAL", "int"), ("NUMERIC", "num"), ("DECIMAL", "num"),
                 ("FLOAT", "num"), ("DOUBLE", "num"), ("REAL", "num"), ("BOOL", "bool"),
                 ("TIMESTAMP", "ts"), ("DATETIME", "ts"), ("DATE", "date"), ("TIME", "time"),
                 ("JSON", "json"), ("CHAR", "text"), ("TEXT", "text"), ("UUID", "uuid"))


def _tipo_corto(tipo: str) -> str:
    t = (tipo or "").upper()
    for clave, corto in _TIPOS_CORTOS:
        if clave in t:
            return corto
    return t.lower()[:10] or "?"


def _linea(r) -> str:
    """Una tabla por linea: 'tabla(col tipo, col tipo PK, id_x FK->tabla)'.

    Cuatro veces menos tokens que CREATE TABLE completo. En CPU sin GPU el
    modelo procesa unos 10 tokens por segundo del prompt, asi que cada columna
    de mas son segundos de espera para el usuario.
    """
    partes = []
    for c in r.columnas:
        p = f"{c.nombre} {_tipo_corto(c.tipo)}"
        if c.es_pk:
            p += " PK"
        if c.fk:
            p += f" FK>{str(c.fk).split('.')[0]}"
        partes.append(p)
    return f"{r.nombre_completo}({', '.join(partes)})"


def ddl_para_pregunta(esquema, pregunta: str) -> str:
    """El esquema que se inyecta al prompt: tablas relevantes + indice del resto."""
    elegidas, resto = relaciones_para_pregunta(esquema, pregunta)
    cuerpo = "\n".join(_linea(r) for r in _sin_ruido(elegidas))
    ddl = _NOTA_BORRADO + cuerpo
    # El indice con el nombre de las demas tablas se quito: eran ~1,300 tokens
    # por pregunta (2 minutos de CPU) y el modelo ya sabe que solo ve las de arriba.
    return ddl
