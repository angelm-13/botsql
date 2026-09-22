"""Barrera de seguridad: un SELECT, de solo lectura, sobre lo que si existe.

Por que no basta con `sql.upper().startswith("SELECT")`
-------------------------------------------------------
Es la validacion que todo el mundo escribe primero y no detiene nada de lo
que importa. Todo esto empieza con SELECT:

    SELECT 1; DROP TABLE facturas                  -- dos enunciados
    SELECT * FROM usuarios INTO OUTFILE '/tmp/x'   -- escribe en disco (MySQL)
    SELECT pg_read_file('/etc/passwd')             -- lee el sistema (PostgreSQL)
    SELECT * FROM usuarios WHERE pg_sleep(60)      -- negacion de servicio
    SELECT password_hash FROM usuarios             -- fuga, y es un SELECT valido
    WITH x AS (DELETE FROM f RETURNING *) SELECT * FROM x  -- ni empieza con SELECT

Las cuatro barreras
-------------------
1. Este validador, ANTES de que el SQL llegue a la base.
2. El usuario de base de datos: conectarse con un rol que solo tiene
   `GRANT SELECT`. Es la unica barrera que no depende de que este codigo sea
   perfecto, y por eso es la que mas importa. El modulo no la puede imponer
   -- se configura en la cadena de conexion -- pero `advertencias_de_despliegue()`
   la reclama en voz alta.
3. La transaccion de solo lectura y el reloj (`executor.py`).
4. El tope de filas al traerlas (`fetchmany`), que no depende de que el
   motor soporte LIMIT.

La trampa del "update"
----------------------
Buscar la palabra `update` en la cadena rompe con `last_update_date`, que
existe en casi toda tabla de un ERP. Y al reves: buscar palabras completas
sin quitar antes los literales rechaza `WHERE nota = 'update'`, que es
legitimo. Por eso aqui primero se limpian comentarios y literales, y solo
despues se buscan palabras completas sobre el esqueleto que queda.

(Este archivo generaliza a varios motores la logica que ya corre en el
asistente acoplado de TYAKXA, `backend/app/asistente/seguridad.py`.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase

# Palabras que no pueden aparecer NUNCA como palabra completa fuera de un
# literal, en ningun motor. No es solo DML: `copy` y `outfile` escriben
# archivos, `sleep` es una negacion de servicio de una linea, `into` cubre
# `SELECT ... INTO tabla_nueva`, y `grant` cambia permisos.
#
# `replace`, `comment` y `cluster` NO estan en la lista aunque tambien sean
# comandos: `REPLACE(col,'a','b')` es una funcion de cadena de uso diario, y
# `comment`/`cluster` son nombres de columna comunes. Como comandos solo
# pueden ser el primer enunciado, y eso ya lo bloquean las dos reglas de
# arriba (un solo enunciado, y tiene que empezar con SELECT o WITH).
PROHIBIDAS_UNIVERSALES: frozenset[str] = frozenset({
    "insert", "update", "delete", "merge", "upsert", "truncate",
    "drop", "create", "alter", "rename", "grant", "revoke",
    "vacuum", "analyze", "reindex", "copy", "call", "do",
    "execute", "exec", "prepare", "deallocate", "declare", "listen",
    "notify", "lock", "unlock", "refresh", "import", "export", "attach",
    "detach", "set", "reset", "discard", "begin", "commit", "rollback",
    "savepoint", "into", "outfile", "dumpfile", "sleep", "benchmark",
    "shutdown", "kill", "waitfor", "delay",
})

# Funciones y objetos peligrosos que si son especificos de un motor.
PROHIBIDAS_POR_MOTOR: dict[str, frozenset[str]] = {
    "postgresql": frozenset({
        "dblink", "pg_sleep", "pg_read_file", "pg_read_binary_file",
        "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export",
        "pg_terminate_backend", "pg_cancel_backend", "pg_logdir_ls",
    }),
    "mysql": frozenset({"load_file", "load", "benchmark", "sys_exec", "sys_eval"}),
    "mariadb": frozenset({"load_file", "load", "benchmark", "sys_exec", "sys_eval"}),
    "sqlite": frozenset({"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}),
    "mssql": frozenset({
        "xp_cmdshell", "sp_executesql", "openrowset", "opendatasource",
        "openquery", "bulk", "xp_dirtree", "xp_fileexist", "sp_oacreate",
    }),
    "oracle": frozenset({"utl_file", "utl_http", "dbms_lock", "dbms_scheduler", "dbms_java"}),
}

# Catalogos del sistema: se bloquea leerlos, no solo escribirlos. Un
# `SELECT * FROM pg_shadow` es un SELECT perfectamente valido.
PREFIJOS_DE_SISTEMA: tuple[str, ...] = (
    "pg_", "information_schema", "mysql.", "performance_schema", "sys.",
    "sqlite_", "sysobjects", "syscolumns", "master.", "msdb.", "dba_",
    "all_tab", "user_tab", "v$",
)

# Motores donde `LIMIT n` es sintaxis valida. En los demas el tope de filas
# lo impone `executor.py` al traerlas.
MOTORES_CON_LIMIT: frozenset[str] = frozenset({"postgresql", "mysql", "mariadb", "sqlite"})


class SqlRechazado(Exception):
    """El SQL no paso la validacion. Nunca llega a la base."""

    def __init__(self, motivo: str, detalle: str = ""):
        self.motivo = motivo
        self.detalle = detalle
        super().__init__(f"{motivo}{f': {detalle}' if detalle else ''}")

    def a_dict(self) -> dict:
        return {"motivo": self.motivo, "detalle": self.detalle, "mensaje": str(self)}


@dataclass(frozen=True)
class SqlValidado:
    sql: str                            # el SQL final, ya acotado
    relaciones: tuple[str, ...]         # lo que lee
    limite: int
    se_agrego_limite: bool


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

_COMENTARIO_LINEA = re.compile(r"--[^\n]*")
_COMENTARIO_BLOQUE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LITERAL_SIMPLE = re.compile(r"'(?:''|\\.|[^'\\])*'", re.DOTALL)
_LITERAL_DOLAR = re.compile(r"\$[A-Za-z_]*\$.*?\$[A-Za-z_]*\$", re.DOTALL)
_LITERAL_CORCHETE = re.compile(r"\[[^\]]*\]")          # identificadores de T-SQL


def sin_comentarios(sql: str) -> str:
    """El SQL sin comentarios, pero con sus literales intactos.

    ESTE es el texto que se ejecuta. Los comentarios se quitan por una razon
    concreta: un `-- algo` al final se tragaria el `LIMIT` que se agrega
    despues, dejando la consulta sin tope.
    """
    sql = _COMENTARIO_BLOQUE.sub(" ", sql)
    return _COMENTARIO_LINEA.sub(" ", sql)


def esqueleto(sql: str) -> str:
    """El SQL sin comentarios y ADEMAS con los literales vaciados.

    Sobre este texto -- y solo sobre este -- se inspecciona: se cuentan
    enunciados y se buscan palabras prohibidas, sin que `WHERE nota =
    'update'` cuente como un UPDATE.

    Nunca se ejecuta. Vaciar los literales cambia lo que la consulta
    significa: ejecutar el esqueleto convertiria `WHERE ciudad = 'CDMX'` en
    `WHERE ciudad = ''` y devolveria cero filas sin que nadie entienda por
    que.
    """
    sql = sin_comentarios(sql)
    sql = _LITERAL_DOLAR.sub(" '' ", sql)
    return _LITERAL_SIMPLE.sub(" '' ", sql)


def _palabras(texto: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z_0-9$]*", texto.lower()))


# ---------------------------------------------------------------------------
# Que relaciones toca
# ---------------------------------------------------------------------------

_DESPUES_DE_FROM = re.compile(
    r"\b(?:from|join)\s+([\"`\[]?[a-zA-Z_][a-zA-Z_0-9$.\"`\]]*)",
    re.IGNORECASE,
)
_ALIAS_DE_CTE = re.compile(r"\b([a-zA-Z_][a-zA-Z_0-9]*)\s*(?:\([^)]*\))?\s+as\s*\(",
                           re.IGNORECASE)


def _limpiar_identificador(bruto: str) -> str:
    return bruto.strip().strip('"').strip("`").strip("[").strip("]").lower()


def relaciones_referenciadas(sql: str) -> tuple[str, ...]:
    """Las tablas o vistas que el SQL lee, sin contar los CTE que el define.

    Un CTE (`WITH reciente AS (...) SELECT * FROM reciente`) no es una tabla:
    si no se descuenta, toda consulta con WITH se rechazaria por "relacion
    desconocida", y el modelo escribe WITH todo el tiempo para los rankings.
    """
    texto = esqueleto(sql)
    ctes = {n.lower() for n in _ALIAS_DE_CTE.findall(texto)}
    encontradas: list[str] = []
    for bruto in _DESPUES_DE_FROM.findall(texto):
        nombre = _limpiar_identificador(bruto)
        corto = nombre.split(".")[-1] if "." in nombre else nombre
        if corto in ctes or not corto:
            continue
        if nombre not in encontradas:
            encontradas.append(nombre)
    return tuple(encontradas)


# ---------------------------------------------------------------------------
# Validacion
# ---------------------------------------------------------------------------

def validar_sql(
    sql: str,
    relaciones_permitidas: frozenset[str] | set[str],
    *,
    motor: str = "postgresql",
    limite_maximo: int = 1000,
    columnas_ocultas: tuple[str, ...] = (),
) -> SqlValidado:
    """Deja pasar un unico SELECT de solo lectura sobre relaciones conocidas.

    Levanta `SqlRechazado` con un motivo legible en cualquier otro caso. El
    motivo viaja hasta el frontend a proposito: un rechazo que no explica
    nada hace que la gente reintente a ciegas.
    """
    if not sql or not sql.strip():
        raise SqlRechazado("sql_vacio")

    crudo = sql.strip()
    # Dos textos, con dos propositos que no se deben mezclar: `ejecutable` es
    # lo que va a correr, `limpio` es sobre lo que se decide si puede correr.
    ejecutable = sin_comentarios(crudo).strip().rstrip(";").rstrip()
    limpio = esqueleto(crudo).strip()

    # -- un solo enunciado ---------------------------------------------------
    sin_final = limpio.rstrip().rstrip(";")
    if ";" in sin_final:
        raise SqlRechazado("varios_enunciados",
                           "solo se permite una consulta por peticion")

    # -- tiene que empezar leyendo ------------------------------------------
    if not re.match(r"^\s*(select|with)\b", sin_final, re.IGNORECASE):
        raise SqlRechazado("no_es_lectura", "la consulta debe empezar con SELECT o WITH")

    # -- palabras prohibidas -------------------------------------------------
    palabras = _palabras(sin_final)
    prohibidas = PROHIBIDAS_UNIVERSALES | PROHIBIDAS_POR_MOTOR.get(motor, frozenset())
    encontradas = sorted(palabras & prohibidas)
    if encontradas:
        raise SqlRechazado("palabra_prohibida", ", ".join(encontradas))

    # -- un CTE que escribe empieza con WITH y ya cayo arriba; explicito ----
    if re.search(r"\bwith\b.*\b(insert|update|delete|merge)\b",
                 sin_final, re.IGNORECASE | re.DOTALL):
        raise SqlRechazado("cte_que_escribe")

    # -- catalogos del sistema ----------------------------------------------
    minusculas = sin_final.lower()
    for prefijo in PREFIJOS_DE_SISTEMA:
        if re.search(rf"\b{re.escape(prefijo)}", minusculas):
            raise SqlRechazado("catalogo_del_sistema", prefijo)

    # -- columnas que el extractor decidio no exponer ------------------------
    if columnas_ocultas:
        nombradas = sorted(
            p for p in palabras
            if any(fnmatchcase(p, patron.lower()) for patron in columnas_ocultas)
        )
        if nombradas:
            raise SqlRechazado("columna_sensible", ", ".join(nombradas))

    # -- solo relaciones que existen y estan permitidas ---------------------
    relaciones = relaciones_referenciadas(crudo)
    if not relaciones:
        raise SqlRechazado("sin_origen", "la consulta no lee de ninguna tabla conocida")

    permitidas = {r.lower() for r in relaciones_permitidas}
    desconocidas = [
        r for r in relaciones
        if r not in permitidas and r.split(".")[-1] not in permitidas
    ]
    if desconocidas:
        raise SqlRechazado(
            "relacion_no_permitida",
            f"{', '.join(desconocidas)} no esta en el esquema expuesto",
        )

    sql_final, limite, agregado = forzar_limite(
        ejecutable, limite_maximo, motor, esqueleto_final=sin_final,
    )

    return SqlValidado(
        sql=sql_final,
        relaciones=relaciones,
        limite=limite,
        se_agrego_limite=agregado,
    )


_LIMIT_FINAL = re.compile(r"\blimit\s+(\d+)\s*$", re.IGNORECASE)


def forzar_limite(sql: str, limite_maximo: int, motor: str,
                  *, esqueleto_final: str | None = None) -> tuple[str, int, bool]:
    """Garantiza que la consulta traiga un tope, donde el motor lo permita.

    Se opera sobre el final del texto a proposito: reescribir el arbol de la
    consulta para meter el LIMIT en el lugar "correcto" de una subconsulta es
    justo el tipo de reescritura que introduce errores silenciosos.

    `esqueleto_final` -- el mismo SQL con los literales vaciados -- es lo que
    se mira para saber si ya hay un LIMIT. Asi, un `WHERE nota = 'limit 5'`
    no se confunde con un tope de verdad. El reemplazo se hace sobre el SQL
    real, donde el `LIMIT n` ocupa exactamente la misma posicion final.

    En SQL Server y Oracle no se toca el texto -- inyectar `TOP` o
    `FETCH FIRST` a ciegas rompe consultas validas -- y el tope lo impone el
    ejecutor al traer las filas, que es la garantia que de verdad cuenta.
    """
    texto = sql.rstrip().rstrip(";").rstrip()

    if motor not in MOTORES_CON_LIMIT:
        return texto, limite_maximo, False

    m = _LIMIT_FINAL.search(esqueleto_final if esqueleto_final is not None else texto)
    if m:
        pedido = int(m.group(1))
        if pedido <= limite_maximo:
            return texto, pedido, False
        return _LIMIT_FINAL.sub(f"LIMIT {limite_maximo}", texto), limite_maximo, True
    return f"{texto}\nLIMIT {limite_maximo}", limite_maximo, True


# ---------------------------------------------------------------------------
# Higiene del despliegue
# ---------------------------------------------------------------------------

_USUARIOS_PRIVILEGIADOS = ("postgres", "root", "sa", "admin", "sysdba")


def advertencias_de_despliegue(database_url: str) -> list[str]:
    """Revisa la cadena de conexion y grita lo que este mal.

    La barrera que de verdad protege no es este archivo: es conectarse con un
    rol que solo tiene `GRANT SELECT`. Como el modulo no puede imponerlo, al
    menos lo hace visible en `/health` en vez de dejarlo a la buena fe.
    """
    avisos: list[str] = []
    if not database_url:
        return ["No hay DATABASE_URL configurada."]

    bajo = database_url.lower()
    usuario = ""
    if "://" in bajo and "@" in bajo:
        usuario = bajo.split("://", 1)[1].split("@", 1)[0].split(":", 1)[0]

    if usuario in _USUARIOS_PRIVILEGIADOS:
        avisos.append(
            f"La conexion usa el superusuario '{usuario}'. Cree un rol de solo "
            "lectura con GRANT SELECT y use ese: es la unica barrera que no "
            "depende de que el validador sea perfecto."
        )
    if bajo.startswith("sqlite"):
        avisos.append(
            "SQLite no soporta tiempo maximo por instruccion: una consulta "
            "pesada solo se corta por el tope de filas."
        )
    return avisos
