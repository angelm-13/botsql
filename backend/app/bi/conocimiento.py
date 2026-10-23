"""Base de conocimiento del sistema: responde lo que NO esta en la base de datos.

El modulo BI contesta preguntas de datos con SQL. Pero mucho de lo que la gente
pregunta del sistema no es un dato: que es un vale, como se timbra una factura,
que puede ver mi rol. Eso vive en la documentacion, y aqui se busca.

Lo que cada persona recibe depende de su rol
--------------------------------------------
El modelo solo ve fragmentos que el rol del usuario puede leer segun el Gestor de
roles y permisos (`entity_permission`, `nm_field_permission`; ver acceso.py):

  * MANUALES (`conocimiento/modulos/*.md`): cada archivo declara en su cabecera
    `entidades_clave: [tablas]`. El manual se entrega solo si el rol puede LEER
    al menos una de ellas. Sin entidades (`[]`) lo ve cualquiera.
  * AYUDA GENERAL (`conocimiento/*.md`): glosario y guia del BI, para todos.
  * GENERADOS AL VUELO, siempre al dia y propios de cada rol:
      - "Mis permisos": que puede leer / crear / editar / eliminar el rol y con
        que alcance (Propios, Mis grupos, Todos).
      - "Modulos disponibles": solo los modulos de los que el rol lee algo.
      - "Estructura de la tabla X": columnas y relaciones, tomadas del esquema
        YA FILTRADO del rol: una columna que no puede leer no aparece.
  * TECNICO (`BI_KB_ADMIN_DIRS`): arquitectura, seguridad, operacion. Solo
    administrador: trae procedimientos e infraestructura internos.

Por pregunta se eligen los 3 fragmentos mas parecidos (palabras en comun, con el
mismo recorte de plurales y los mismos sinonimos espanol->tabla que usa
`schema_linking`) y el modelo contesta SOLO con eso; si no esta, lo admite.
"""

from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .schema_linking import SINONIMOS, _raiz

CARPETA_GENERAL = Path(__file__).with_name("conocimiento")
MAX_FRAGMENTO = 900
MAX_CONTEXTO = 2600
TTL_S = 300

# Preguntas "de sistema" (no de datos). Se evaluan sobre el texto sin acentos.
_ES_DE_SISTEMA = re.compile(
    r"^(como|donde|cuando|para que|por que|porque|quien|quienes puede|que (es|son|significa|significan|hace|hacen|"
    r"diferencia|modulos|pantallas|roles|permisos|puedo|se necesita|pasa|campos|datos tiene|informacion tiene)|"
    r"explica|explicame|cuales son (los|las) (modulos|pantallas|roles|permisos|pasos|funciones|reglas|campos)|"
    r"ayuda|de que (trata|sirve)|en que consiste|a que (tengo|puedo)|mis permisos|que (tablas|datos) puedo)\b")


def _norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip(" ?!.¿¡")


def es_pregunta_de_sistema(pregunta: str) -> bool:
    """True si la pregunta pide explicacion/ayuda y no un dato."""
    return bool(_ES_DE_SISTEMA.search(_norm(pregunta)))


@dataclass(frozen=True)
class Fragmento:
    fuente: str
    titulo: str
    texto: str
    tokens: frozenset
    clave: frozenset = frozenset()       # entidades; el rol debe leer al menos una
    solo_admin: bool = False


def _tokens(t: str) -> frozenset:
    return frozenset(_raiz(p) for p in re.findall(r"[a-z0-9]{3,}", _norm(t)))


def _cabecera(md: str) -> tuple[dict, str]:
    """Separa la cabecera `--- ... ---` (modulo, entidades_clave) del cuerpo."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, re.S)
    if not m:
        return {}, md
    datos: dict = {}
    for linea in m.group(1).splitlines():
        k, _, v = linea.partition(":")
        v = v.split("#", 1)[0].strip()
        if v.startswith("["):
            datos[k.strip()] = frozenset(x.strip().lower() for x in v.strip("[]").split(",") if x.strip())
        else:
            datos[k.strip()] = v
    return datos, md[m.end():]


def _partir(fuente: str, md: str, *, clave=frozenset(), solo_admin=False) -> list[Fragmento]:
    """Parte un Markdown por encabezados y recorta secciones largas por parrafo."""
    salida: list[Fragmento] = []
    titulo, cuerpo = fuente, []

    def nuevo(bloque: str):
        salida.append(Fragmento(fuente, titulo, bloque, _tokens(titulo + " " + bloque), clave, solo_admin))

    def cerrar():
        texto = "\n".join(cuerpo).strip()
        if len(texto) < 40:
            return
        bloque = ""
        for parr in re.split(r"\n\s*\n", texto):
            if bloque and len(bloque) + len(parr) > MAX_FRAGMENTO:
                nuevo(bloque)
                bloque = ""
            bloque += ("\n\n" if bloque else "") + parr
        if bloque:
            nuevo(bloque)

    for linea in md.splitlines():
        m = re.match(r"^#{1,4}\s+(.*)", linea)
        if m:
            cerrar()
            titulo, cuerpo = m.group(1).strip(), []
        else:
            cuerpo.append(linea)
    cerrar()
    return salida


def _leer_md(carpetas: list[Path], *, solo_admin: bool) -> list[Fragmento]:
    salida: list[Fragmento] = []
    for base in carpetas:
        if not base.exists():
            continue
        archivos = [base] if base.is_file() else sorted(base.rglob("*.md"))
        for f in archivos:
            try:
                cab, cuerpo = _cabecera(f.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            clave = cab.get("entidades_clave", frozenset())
            salida.extend(_partir(f.name, cuerpo, clave=clave if isinstance(clave, frozenset) else frozenset(),
                                  solo_admin=solo_admin))
    return salida


# ---------------------------------------------------------------------------
# Fragmentos generados al vuelo, propios del rol
# ---------------------------------------------------------------------------

_ALCANCE = {0: "sin acceso", 1: "solo lo propio", 2: "lo de mis grupos", 4: "todo"}


def _modulos():
    try:
        from app.modules.registry import MODULOS
        return MODULOS
    except Exception:
        return ()


def _frag(titulo: str, texto: str, fuente: str = "datos del sistema") -> Fragmento:
    return Fragmento(fuente, titulo, texto, _tokens(titulo + " " + texto))


def _puede_leer(acceso, entidad: str) -> bool:
    return acceso is not None and (acceso.es_admin or acceso.permite_tabla(entidad))


def _dinamicos(acceso, esquema) -> list[Fragmento]:
    if acceso is None:
        return []
    mods = _modulos()
    visibles = [m for m in mods if any(_puede_leer(acceso, e) for e in m.entidades)]
    salida: list[Fragmento] = []

    nombres = ", ".join(m.etiqueta for m in visibles) or "ninguno"
    salida.append(_frag("Modulos disponibles para mi rol (que modulos puedo ver)",
                        f"Los modulos del sistema que tu rol puede consultar son: {nombres}. "
                        "Cada modulo agrupa sus pantallas y permisos. Los modulos que no aparecen aqui "
                        "no estan habilitados para tu rol; pide acceso al administrador."))

    if acceso.es_admin:
        salida.append(_frag("Mis permisos y mi rol",
                            f"Tu rol es {acceso.rol or 'Administrador'}. Como administrador puedes leer, crear, "
                            "editar y eliminar en todos los modulos habilitados en el plan del sistema, y ver "
                            "todas las tablas y columnas en el Analisis BI."))
    else:
        por_modulo: dict[str, list[str]] = {}
        dueno = {e: m.etiqueta for m in mods for e in m.entidades}
        for ent, crear, leer, editar, borrar in acceso.permisos:
            if leer == 0 and crear == 0 and editar == 0 and borrar == 0:
                continue
            partes = []
            if leer:
                partes.append(f"ver ({_ALCANCE.get(leer, leer)})")
            if crear:
                partes.append(f"crear ({_ALCANCE.get(crear, crear)})")
            if editar:
                partes.append(f"editar ({_ALCANCE.get(editar, editar)})")
            if borrar:
                partes.append(f"eliminar ({_ALCANCE.get(borrar, borrar)})")
            por_modulo.setdefault(dueno.get(ent, "otras pantallas"), []).append(f"{ent}: {', '.join(partes)}")
        salida.append(_frag("Mis permisos y mi rol",
                            f"Tu rol es {acceso.rol or 'sin nombre'}. Estos permisos vienen del Gestor de roles "
                            "y permisos. Puedes consultar en el Analisis BI las tablas con permiso de ver."))
        for modulo, lineas in sorted(por_modulo.items()):
            texto = f"En el modulo {modulo} tu rol puede: " + "; ".join(lineas) + "."
            for i in range(0, len(texto), MAX_FRAGMENTO):
                salida.append(_frag(f"Mis permisos en {modulo} (que puedo ver, crear, editar o eliminar)",
                                    texto[i:i + MAX_FRAGMENTO]))
        if acceso.columnas_negadas:
            salida.append(_frag("Columnas que mi rol no puede ver",
                                "Tu rol no puede ver estas columnas (por ejemplo importes): "
                                + ", ".join(sorted(acceso.columnas_negadas)) + "."))

    if esquema is not None:
        dueno = {e: m.etiqueta for m in mods for e in m.entidades}
        for r in esquema.relaciones:
            cols = ", ".join(f"{c.nombre} ({c.tipo.split('(')[0].lower()})" for c in r.columnas
                             if c.nombre.lower() not in ("created_by", "creation_date", "last_update_date"))
            rel = ", ".join(sorted({str(c.fk).split(".")[0] for c in r.columnas if c.fk}))
            texto = f"La tabla {r.nombre} (modulo {dueno.get(r.nombre.lower(), 'general')}) tiene los campos: {cols}."
            if rel:
                texto += f" Se relaciona con: {rel}."
            # Nombre en espanol de la tabla (producto -> product), para que "que campos
            # tiene un producto" encuentre `product` y no una tabla que lo menciona.
            alias = sorted({k for k, v in SINONIMOS.items() if r.nombre.lower() in v})[:3]
            etiqueta = f" ({', '.join(alias)})" if alias else ""
            salida.append(_frag(f"Estructura de la tabla {r.nombre}{etiqueta} (campos y datos que contiene)",
                                texto[:MAX_FRAGMENTO]))
    return salida


# ---------------------------------------------------------------------------
# Carga y busqueda
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_estaticos: tuple[float, list[Fragmento]] | None = None
_por_perfil: dict[str, tuple[float, list[Fragmento]]] = {}


def _cargar_estaticos() -> list[Fragmento]:
    global _estaticos
    with _lock:
        if _estaticos and _estaticos[0] > time.time():
            return _estaticos[1]
    lista = _leer_md([CARPETA_GENERAL], solo_admin=False)
    extra = [Path(p) for p in os.environ.get("BI_KB_ADMIN_DIRS", "").split(os.pathsep) if p.strip()]
    lista += _leer_md(extra, solo_admin=True)
    with _lock:
        _estaticos = (time.time() + TTL_S, lista)
    return lista


def fragmentos(acceso, esquema=None) -> list[Fragmento]:
    """Lo que ESTE usuario puede consultar en la documentacion."""
    es_admin = bool(acceso is not None and acceso.es_admin)
    perfil = f"{getattr(acceso, 'clave', 'anon')}|{getattr(esquema, 'huella', '')}"
    with _lock:
        previo = _por_perfil.get(perfil)
        if previo and previo[0] > time.time():
            return previo[1]
    visibles = []
    for f in _cargar_estaticos():
        if f.solo_admin and not es_admin:
            continue
        if f.clave and not es_admin and not any(_puede_leer(acceso, e) for e in f.clave):
            continue
        visibles.append(f)
    visibles += _dinamicos(acceso, esquema)
    with _lock:
        _por_perfil[perfil] = (time.time() + TTL_S, visibles)
    return visibles


def invalidar() -> None:
    global _estaticos
    with _lock:
        _estaticos = None
        _por_perfil.clear()


def _expandir(tokens: frozenset) -> frozenset:
    extra = set(tokens)
    for t in tokens:
        for clave, frags in SINONIMOS.items():
            if t == _raiz(clave):
                extra.update(_raiz(f) for f in frags)
    return frozenset(extra)


def buscar(pregunta: str, acceso=None, esquema=None, k: int = 3) -> list[Fragmento]:
    q = _tokens(pregunta)
    if not q:
        return []
    qx = _expandir(q)
    puntuados = []
    for f in fragmentos(acceso, esquema):
        directos = q & f.tokens
        sinonimos = (qx - q) & f.tokens
        if not directos and not sinonimos:
            continue
        titulo = (q | (qx - q)) & _tokens(f.titulo)
        puntuados.append((2 * len(directos) + len(sinonimos) + 3 * len(titulo), f))
    puntuados.sort(key=lambda x: -x[0])
    elegidos, total = [], 0
    for puntos, f in puntuados[:k]:
        if puntos < 4:
            break
        if total + len(f.texto) > MAX_CONTEXTO and elegidos:
            break
        elegidos.append(f)
        total += len(f.texto)
    return elegidos


PLANTILLA = """Eres el asistente de ayuda del sistema TYAKXA (ERP). Responde en espanol, de forma clara y breve (maximo 6 lineas), usando UNICAMENTE la DOCUMENTACION de abajo, que ya esta limitada a lo que el rol de esta persona puede ver. Si la documentacion no contiene la respuesta, responde exactamente: "No encontre eso en la documentacion a la que tu rol tiene acceso." No inventes pantallas, pasos ni datos. Responde SOLO con JSON: {{"respuesta": "..."}}

### DOCUMENTACION:
{contexto}

### PREGUNTA:
{pregunta}"""


def construir_prompt(pregunta: str, trozos: list[Fragmento]) -> str:
    contexto = "\n\n".join(f"[{f.titulo}]\n{f.texto}" for f in trozos) or "(sin documentacion relacionada)"
    return PLANTILLA.format(contexto=contexto, pregunta=pregunta)


ESQUEMA_TEXTO = {
    "type": "object",
    "properties": {"respuesta": {"type": "string"}},
    "required": ["respuesta"],
}
