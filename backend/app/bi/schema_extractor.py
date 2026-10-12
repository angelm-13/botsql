"""PASO 1 -- Extractor dinamico de esquema.

Inspecciona la base conectada con `sqlalchemy.inspect` y produce el DDL que
se le inyecta al modelo. Funciona sobre PostgreSQL, MySQL/MariaDB, SQLite y
SQL Server sin una sola rama por motor: el `Inspector` de SQLAlchemy ya
normaliza las diferencias. Lo unico que cambia por motor es como se citan los
identificadores, y de eso se encarga el `identifier_preparer` del dialecto.

Tres decisiones que no son obvias
---------------------------------
1. **Filtrar antes de generar.** Darle las 120 tablas de un ERP al modelo
   cuesta miles de tokens, y la mitad son fontaneria (`session`, `*_token`).
   Un prompt grande no solo es lento: hace que el modelo invente uniones
   entre tablas que no tienen nada que ver. `AjustesBI.incluir/excluir`
   deciden que entra, y `max_tablas` pone un tope duro.

2. **Las columnas ocultas no se ocultan: no existen.** Una columna que
   coincide con `columnas_ocultas` no aparece en el DDL. El modelo no puede
   pedir lo que no sabe que existe, y ademas `security.py` rechaza cualquier
   SQL que la nombre. Son dos barreras, no una.

3. **Las llaves foraneas se emiten como comentario, no como constraint.**
   El modelo no va a crear la tabla: va a escribir un JOIN. `-- FK ->
   clientes.id` en la linea de la columna es lo que realmente lee, y ocupa
   menos que un bloque `FOREIGN KEY (...) REFERENCES (...)` al final.

La cache (`CacheDeEsquema`) evita re-inspeccionar en cada pregunta. Se
invalida por TTL, y al re-extraer se compara la huella: si no cambio, nada
aguas abajo tiene que rearmarse.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from sqlalchemy import Engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# Nombre legible del motor, para que el prompt diga "PostgreSQL" y no
# "postgresql". El modelo escribe mejor SQL cuando el motor se nombra como
# aparece en su documentacion.
NOMBRE_DEL_MOTOR: dict[str, str] = {
    "postgresql": "PostgreSQL",
    "mysql": "MySQL / MariaDB",
    "mariadb": "MariaDB",
    "sqlite": "SQLite",
    "mssql": "Microsoft SQL Server (T-SQL)",
    "oracle": "Oracle Database",
    "snowflake": "Snowflake",
}

# Como se acota el numero de filas en cada motor. Entra al prompt para que el
# modelo no escriba `LIMIT 10` contra SQL Server, que no lo soporta.
SINTAXIS_DE_LIMITE: dict[str, str] = {
    "postgresql": "LIMIT n",
    "mysql": "LIMIT n",
    "mariadb": "LIMIT n",
    "sqlite": "LIMIT n",
    "mssql": "SELECT TOP (n) ... -- este motor NO soporta LIMIT",
    "oracle": "FETCH FIRST n ROWS ONLY",
}

# Tipos cuyos valores de ejemplo ayudan al modelo (un estatus, una categoria).
# Un texto libre o un blob no ayudan y ocupan tokens.
_TIPOS_MUESTREABLES = ("VARCHAR", "CHAR", "TEXT", "ENUM", "NVARCHAR")


@dataclass(frozen=True)
class Columna:
    nombre: str
    tipo: str
    nullable: bool = True
    es_pk: bool = False
    fk: str | None = None            # "tabla.columna" a la que apunta
    comentario: str = ""
    muestras: tuple[str, ...] = ()

    def a_ddl(self, ancho_nombre: int = 0) -> str:
        linea = f"    {self.nombre.ljust(ancho_nombre)} {self.tipo}"
        if not self.nullable:
            linea += " NOT NULL"

        notas: list[str] = []
        if self.es_pk:
            notas.append("PK")
        if self.fk:
            notas.append(f"FK -> {self.fk}")
        if self.comentario:
            notas.append(self.comentario.strip().splitlines()[0][:80])
        if self.muestras:
            notas.append("valores: " + ", ".join(self.muestras))
        if notas:
            linea += "  -- " + "; ".join(notas)
        return linea


@dataclass(frozen=True)
class Relacion:
    """Una tabla o vista que el modelo puede consultar."""

    nombre: str
    columnas: tuple[Columna, ...]
    es_vista: bool = False
    esquema: str | None = None
    comentario: str = ""
    columnas_omitidas: tuple[str, ...] = ()

    @property
    def nombre_completo(self) -> str:
        return f"{self.esquema}.{self.nombre}" if self.esquema else self.nombre

    def a_ddl(self) -> str:
        ancho = max((len(c.nombre) for c in self.columnas), default=0)
        clase = "VIEW" if self.es_vista else "TABLE"

        lineas: list[str] = []
        if self.comentario:
            lineas.append(f"-- {self.comentario.strip().splitlines()[0][:120]}")
        lineas.append(f"CREATE {clase} {self.nombre_completo} (")
        lineas.append(",\n".join(c.a_ddl(ancho) for c in self.columnas))
        lineas.append(");")
        if self.columnas_omitidas:
            lineas.append(
                f"-- {len(self.columnas_omitidas)} columna(s) sensibles omitidas "
                "a proposito: no existen para este modulo."
            )
        return "\n".join(lineas)


@dataclass(frozen=True)
class EsquemaDB:
    """El esquema ya filtrado, listo para inyectarse en el prompt."""

    motor: str                              # dialecto de SQLAlchemy: "postgresql"
    motor_legible: str                      # "PostgreSQL"
    version: str
    relaciones: tuple[Relacion, ...]
    total_encontradas: int                  # antes de filtrar
    excluidas: tuple[str, ...] = ()
    truncado: bool = False                  # se corto por `max_tablas`
    generado_en: float = field(default_factory=time.time)

    @property
    def nombres(self) -> frozenset[str]:
        """Los nombres consultables, para el validador de seguridad.

        Incluye el nombre corto y el calificado por esquema: el modelo puede
        escribir cualquiera de los dos y ambos son legitimos.
        """
        salida: set[str] = set()
        for r in self.relaciones:
            salida.add(r.nombre.lower())
            salida.add(r.nombre_completo.lower())
        return frozenset(salida)

    @property
    def columnas_por_relacion(self) -> dict[str, frozenset[str]]:
        return {
            r.nombre.lower(): frozenset(c.nombre.lower() for c in r.columnas)
            for r in self.relaciones
        }

    @property
    def sintaxis_de_limite(self) -> str:
        return SINTAXIS_DE_LIMITE.get(self.motor, "LIMIT n")

    def a_ddl(self) -> str:
        """El bloque completo que se inyecta como `{dynamic_db_schema}`."""
        encabezado = [
            f"-- Motor: {self.motor_legible} {self.version}".rstrip(),
            f"-- Relaciones consultables: {len(self.relaciones)}"
            + (f" (de {self.total_encontradas} encontradas)"
               if self.total_encontradas != len(self.relaciones) else ""),
            f"-- Sintaxis de acotamiento en este motor: {self.sintaxis_de_limite}",
        ]
        if self.truncado:
            encabezado.append("-- AVISO: el esquema se trunco por tamano.")
        encabezado.append("")
        cuerpo = "\n\n".join(r.a_ddl() for r in self.relaciones)
        return "\n".join(encabezado) + cuerpo

    @property
    def huella(self) -> str:
        """Hash del DDL. Si cambia, hay que rearmar el prompt."""
        return hashlib.sha256(self.a_ddl().encode("utf-8")).hexdigest()[:16]

    def resumen(self) -> dict:
        return {
            "motor": self.motor,
            "motor_legible": self.motor_legible,
            "version": self.version,
            "relaciones": [
                {
                    "nombre": r.nombre_completo,
                    "tipo": "vista" if r.es_vista else "tabla",
                    "columnas": [
                        {"nombre": c.nombre, "tipo": c.tipo, "pk": c.es_pk, "fk": c.fk}
                        for c in r.columnas
                    ],
                    "columnas_omitidas": list(r.columnas_omitidas),
                }
                for r in self.relaciones
            ],
            "total_encontradas": self.total_encontradas,
            "excluidas": list(self.excluidas),
            "truncado": self.truncado,
            "huella": self.huella,
            "generado_en": self.generado_en,
        }


# ---------------------------------------------------------------------------
# Filtrado
# ---------------------------------------------------------------------------

def _coincide(nombre: str, patrones: tuple[str, ...]) -> bool:
    bajo = nombre.lower()
    return any(fnmatchcase(bajo, p.lower()) for p in patrones)


def _entra(nombre: str, incluir: tuple[str, ...], excluir: tuple[str, ...]) -> bool:
    """La lista de inclusion, si existe, manda sobre la de exclusion.

    Es deliberado: quien escribe `incluir=("ventas*",)` esta diciendo
    exactamente que quiere, y no deberia tener que pelearse ademas con la
    lista de exclusion por omision.
    """
    if incluir:
        return _coincide(nombre, incluir)
    return not _coincide(nombre, excluir)


# ---------------------------------------------------------------------------
# Extraccion
# ---------------------------------------------------------------------------

def _version_del_motor(engine: Engine) -> str:
    try:
        with engine.connect() as con:
            info = getattr(con.dialect, "server_version_info", None)
    except SQLAlchemyError:
        return ""
    if not info:
        return ""
    return ".".join(str(p) for p in info[:3])


def acotar_tiempo(con, dialecto: str, timeout_ms: int) -> None:
    """Le pone reloj a la consulta con la instruccion propia de cada motor.

    Ninguna es portable, y por eso vive en un solo lugar. SQLite no tiene
    reloj por instruccion: ahi la unica proteccion real es el tope de filas
    que aplica el ejecutor.
    """
    try:
        if dialecto == "postgresql":
            con.exec_driver_sql(f"SET statement_timeout = {int(timeout_ms)}")
        elif dialecto in ("mysql", "mariadb"):
            con.exec_driver_sql(f"SET SESSION MAX_EXECUTION_TIME = {int(timeout_ms)}")
        elif dialecto == "mssql":
            con.exec_driver_sql(f"SET LOCK_TIMEOUT {int(timeout_ms)}")
    except SQLAlchemyError:
        # Un motor que no acepta la instruccion no debe impedir la consulta;
        # el tope de filas y el timeout del pool siguen en pie.
        pass


def _muestras_de_columna(engine, relacion: str, esquema: str | None,
                         columna: str, cuantas: int, timeout_ms: int) -> tuple[str, ...]:
    """Hasta `cuantas` valores distintos de una columna categorica.

    Es lo que mas sube la precision del texto-a-SQL: sin esto el modelo
    escribe `WHERE estatus = 'pagada'` cuando la base guarda `'PAGADO'`.

    El nombre de tabla y de columna NO vienen del usuario -- salen del
    inspector -- y aun asi se citan con el preparador del dialecto, porque
    `user` y `order` son palabras reservadas en casi todos los motores.
    """
    preparador = engine.dialect.identifier_preparer
    destino = preparador.quote(relacion)
    if esquema:
        destino = f"{preparador.quote(esquema)}.{destino}"
    col = preparador.quote(columna)
    try:
        with engine.connect() as con:
            acotar_tiempo(con, engine.dialect.name, timeout_ms)
            # Sin LIMIT: se acota con fetchmany, que funciona en todo motor.
            filas = con.exec_driver_sql(
                f"SELECT DISTINCT {col} FROM {destino} WHERE {col} IS NOT NULL"
            ).fetchmany(cuantas)
    except SQLAlchemyError:
        return ()
    return tuple(str(f[0])[:40] for f in filas if f[0] is not None)


def extraer_esquema(engine: Engine, ajustes) -> EsquemaDB:
    """Inspecciona la base viva y devuelve su esquema filtrado.

    No importa si detras hay PostgreSQL, MySQL, SQLite o SQL Server: el
    `Inspector` normaliza nombres, tipos, llaves primarias y foraneas.
    """
    inspector = inspect(engine)
    dialecto = engine.dialect.name
    esquemas = ajustes.esquemas or (None,)

    encontradas: list[tuple[str | None, str, bool]] = []
    for esq in esquemas:
        for nombre in inspector.get_table_names(schema=esq):
            encontradas.append((esq, nombre, False))
        if ajustes.incluir_vistas:
            try:
                for nombre in inspector.get_view_names(schema=esq):
                    encontradas.append((esq, nombre, True))
            except NotImplementedError:
                pass

    excluidas: list[str] = []
    elegidas: list[tuple[str | None, str, bool]] = []
    for esq, nombre, es_vista in encontradas:
        if _entra(nombre, ajustes.incluir, ajustes.excluir):
            elegidas.append((esq, nombre, es_vista))
        else:
            excluidas.append(nombre)

    elegidas.sort(key=lambda t: (t[2], t[1]))    # tablas antes que vistas
    truncado = len(elegidas) > ajustes.max_tablas
    elegidas = elegidas[: ajustes.max_tablas]

    relaciones: list[Relacion] = []
    for esq, nombre, es_vista in elegidas:
        relacion = _leer_relacion(engine, inspector, esq, nombre, es_vista, ajustes)
        if relacion is not None and relacion.columnas:
            relaciones.append(relacion)

    return EsquemaDB(
        motor=dialecto,
        motor_legible=NOMBRE_DEL_MOTOR.get(dialecto, dialecto),
        version=_version_del_motor(engine),
        relaciones=tuple(relaciones),
        total_encontradas=len(encontradas),
        excluidas=tuple(sorted(excluidas)),
        truncado=truncado,
    )


def _leer_relacion(engine, inspector, esq, nombre, es_vista, ajustes) -> Relacion | None:
    try:
        columnas_crudas = inspector.get_columns(nombre, schema=esq)
    except SQLAlchemyError:
        # Una vista rota o una tabla sin permisos no debe tumbar la extraccion
        # entera: se omite y el resto del esquema sigue sirviendo.
        return None

    try:
        pk = set(inspector.get_pk_constraint(nombre, schema=esq).get("constrained_columns") or [])
    except (SQLAlchemyError, NotImplementedError):
        pk = set()

    fks: dict[str, str] = {}
    try:
        for fk in inspector.get_foreign_keys(nombre, schema=esq):
            destino = fk.get("referred_table")
            columnas_destino = fk.get("referred_columns") or []
            for i, col in enumerate(fk.get("constrained_columns") or []):
                objetivo = columnas_destino[i] if i < len(columnas_destino) else ""
                fks[col] = f"{destino}.{objetivo}" if objetivo else str(destino)
    except (SQLAlchemyError, NotImplementedError):
        pass

    columnas: list[Columna] = []
    omitidas: list[str] = []
    for cruda in columnas_crudas:
        nombre_col = cruda["name"]
        if _coincide(nombre_col, ajustes.columnas_ocultas):
            omitidas.append(nombre_col)
            continue

        tipo = _tipo_legible(cruda.get("type"))
        muestras: tuple[str, ...] = ()
        if ajustes.con_muestras and any(t in tipo.upper() for t in _TIPOS_MUESTREABLES):
            muestras = _muestras_de_columna(
                engine, nombre, esq, nombre_col,
                ajustes.max_muestras, ajustes.timeout_sql_ms,
            )

        columnas.append(Columna(
            nombre=nombre_col,
            tipo=tipo,
            nullable=bool(cruda.get("nullable", True)),
            es_pk=nombre_col in pk,
            fk=fks.get(nombre_col),
            comentario=(cruda.get("comment") or ""),
            muestras=muestras,
        ))

    comentario = ""
    try:
        comentario = (inspector.get_table_comment(nombre, schema=esq) or {}).get("text") or ""
    except (SQLAlchemyError, NotImplementedError, AttributeError):
        pass

    return Relacion(
        nombre=nombre,
        columnas=tuple(columnas),
        es_vista=es_vista,
        esquema=esq,
        comentario=comentario,
        columnas_omitidas=tuple(omitidas),
    )


def _tipo_legible(tipo) -> str:
    """El tipo como cadena, degradando sin romperse.

    Algunos tipos propios de un motor no saben compilarse fuera de el
    (`geometry` de PostGIS en un dialecto generico). Ahi se usa el nombre de
    la clase, que para el prompt es suficiente.
    """
    if tipo is None:
        return "UNKNOWN"
    try:
        # Una vista de SQLite no declara tipos y el inspector devuelve
        # "NULL", que en el DDL se lee como si la columna fuera nula.
        texto = str(tipo).strip()
        return texto if texto and texto.upper() != "NULL" else "UNKNOWN"
    except Exception:
        return type(tipo).__name__.upper()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class CacheDeEsquema:
    """Guarda el esquema extraido y lo reusa mientras siga vigente.

    Inspeccionar una base de 60 tablas son decenas de consultas al catalogo:
    hacerlo en cada pregunta es la diferencia entre responder en 2 segundos y
    responder en 6.
    """

    def __init__(self, engine: Engine, ajustes):
        self._engine = engine
        self._ajustes = ajustes
        self._lock = threading.Lock()
        self._esquema: EsquemaDB | None = None
        self._vence_en: float = 0.0
        self.aciertos = 0
        self.extracciones = 0

    def obtener(self, *, forzar: bool = False) -> EsquemaDB:
        ahora = time.time()
        with self._lock:
            vigente = self._esquema is not None and ahora < self._vence_en
            if vigente and not forzar:
                self.aciertos += 1
                return self._esquema            # type: ignore[return-value]

            esquema = extraer_esquema(self._engine, self._ajustes)
            self._esquema = esquema
            self._vence_en = ahora + self._ajustes.ttl_esquema_s
            self.extracciones += 1
            return esquema

    def invalidar(self) -> None:
        with self._lock:
            self._esquema = None
            self._vence_en = 0.0

    @property
    def estado(self) -> dict:
        return {
            "aciertos": self.aciertos,
            "extracciones": self.extracciones,
            "vigente_hasta": self._vence_en,
            "huella": self._esquema.huella if self._esquema else None,
        }
