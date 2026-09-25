"""Ajustes del modulo de BI.

Todo lo que cambia entre un proyecto y otro vive aqui y en ningun otro lado.
Conectar el modulo a un ERP distinto es cambiar `database_url` y, si acaso,
las listas de inclusion/exclusion de tablas. No se toca codigo.

Se lee del entorno para que el mismo contenedor sirva en cualquier despliegue,
pero `AjustesBI` es un dataclass normal: quien lo integre como libreria puede
construirlo a mano y nunca pasar por variables de entorno.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field, replace

# Tablas que no son datos de negocio en practicamente ningun sistema. Son
# patrones de fnmatch, no nombres exactos, porque cada ORM las nombra distinto
# (`alembic_version`, `django_migrations`, `flyway_schema_history`).
EXCLUIR_POR_OMISION: tuple[str, ...] = (
    "alembic_version", "*migration*", "*migrations*", "flyway_*", "schema_version",
    "session", "sessions", "*_session", "password_reset*", "*_token", "*_tokens",
    "user_mfa", "*api_key*", "*apikey*", "celery_*", "*_log_raw", "spatial_ref_sys",
)

# Columnas que nunca se le muestran al modelo ni se pueden consultar: si no
# estan en el DDL que ve, no las puede nombrar; y si no las nombra, no salen.
# Es una lista de patrones, y crece por proyecto.
COLUMNAS_OCULTAS_POR_OMISION: tuple[str, ...] = (
    "password", "password_hash", "*_password", "salt", "secret", "*_secret",
    "token", "*_token", "api_key", "*_api_key", "private_key", "*_private_key",
    "mfa_secret", "totp_*", "ssn", "national_id", "curp", "nss",
)


@dataclass(frozen=True)
class AjustesBI:
    """La configuracion completa del modulo."""

    # -- conexion ------------------------------------------------------------
    database_url: str = ""
    esquemas: tuple[str, ...] = ()        # () = el esquema por omision del motor

    # -- que ve el modelo ----------------------------------------------------
    incluir: tuple[str, ...] = ()          # patrones; () = todo lo que no se excluya
    excluir: tuple[str, ...] = EXCLUIR_POR_OMISION
    columnas_ocultas: tuple[str, ...] = COLUMNAS_OCULTAS_POR_OMISION
    incluir_vistas: bool = True
    max_tablas: int = 60                   # tope duro del DDL que entra al prompt
    con_muestras: bool = False             # valores de ejemplo de columnas categoricas
    max_muestras: int = 5

    # -- modelo de lenguaje --------------------------------------------------
    ollama_url: str = "http://localhost:11434"
    # El tag en el registro de Ollama es "qwen2.5-coder:7b" -- sin sufijo
    # "-instruct". Con GPU responde en segundos; medido en CPU pura (sin
    # GPU, hardware de escritorio normal) una pregunta libre tarda entre 60 y
    # 100 segundos, casi todo en la generacion del JSON de respuesta.
    modelo: str = "qwen2.5-coder:7b"
    # 120s alcanza con GPU; en CPU pura una sola pregunta ya mide ~90s de
    # punta a punta (medido de verdad, no estimado) y un tablero de varios
    # widgets puede acercarse al limite. Se sube el doble como margen real,
    # no arbitrario.
    timeout_llm: int = 240
    temperatura: float = 0.0

    # -- ejecucion -----------------------------------------------------------
    limite_filas: int = 1000               # tope duro de filas por consulta
    timeout_sql_ms: int = 15000
    max_widgets: int = 8                   # tope de consultas por dashboard

    # -- cache ---------------------------------------------------------------
    ttl_esquema_s: int = 300               # cada cuanto se re-inspecciona la base

    # -- servidor ------------------------------------------------------------
    prefijo_api: str = "/api/v1/bi"
    cors_origenes: tuple[str, ...] = ("*",)

    def con(self, **cambios) -> "AjustesBI":
        return replace(self, **cambios)

    @classmethod
    def desde_entorno(cls, entorno: dict | None = None) -> "AjustesBI":
        """Construye los ajustes leyendo variables `BI_*`.

        `BI_DATABASE_URL` gana sobre `DATABASE_URL`: asi el modulo puede
        apuntar a una replica de solo lectura sin mover la base que usa la
        aplicacion anfitriona -- que es como deberia desplegarse en serio.
        """
        env = entorno if entorno is not None else os.environ
        base = cls()

        def lista(clave: str, omision: tuple[str, ...]) -> tuple[str, ...]:
            crudo = env.get(clave)
            if crudo is None:
                return omision
            partes = tuple(p.strip() for p in crudo.split(",") if p.strip())
            return partes

        def entero(clave: str, omision: int) -> int:
            try:
                return int(env.get(clave, omision))
            except (TypeError, ValueError):
                return omision

        return cls(
            database_url=env.get("BI_DATABASE_URL") or env.get("DATABASE_URL", ""),
            esquemas=lista("BI_SCHEMAS", base.esquemas),
            incluir=lista("BI_INCLUDE_TABLES", base.incluir),
            excluir=lista("BI_EXCLUDE_TABLES", base.excluir),
            columnas_ocultas=lista("BI_HIDDEN_COLUMNS", base.columnas_ocultas),
            incluir_vistas=env.get("BI_INCLUDE_VIEWS", "1") not in ("0", "false", "False"),
            max_tablas=entero("BI_MAX_TABLES", base.max_tablas),
            con_muestras=env.get("BI_SAMPLE_VALUES", "0") in ("1", "true", "True"),
            ollama_url=env.get("BI_OLLAMA_URL", base.ollama_url),
            modelo=env.get("BI_MODEL", base.modelo),
            timeout_llm=entero("BI_LLM_TIMEOUT", base.timeout_llm),
            limite_filas=entero("BI_ROW_LIMIT", base.limite_filas),
            timeout_sql_ms=entero("BI_SQL_TIMEOUT_MS", base.timeout_sql_ms),
            max_widgets=entero("BI_MAX_WIDGETS", base.max_widgets),
            ttl_esquema_s=entero("BI_SCHEMA_TTL", base.ttl_esquema_s),
            prefijo_api=env.get("BI_API_PREFIX", base.prefijo_api),
            cors_origenes=lista("BI_CORS_ORIGINS", base.cors_origenes),
        )


def puerto_disponible(host: str, puerto: int) -> bool:
    """Si se puede escuchar ahi ahora mismo.

    Se usa para avisar ANTES de arrancar, y no despues. La razon no es
    cosmetica: el servidor de desarrollo de Werkzeug atrapa el `OSError` del
    bind el mismo -- imprime su propio mensaje y llama a `sys.exit(1)`
    directamente, sin volver a levantar la excepcion -- asi que envolver
    `aplicacion.run(...)` en un `try/except OSError` en el codigo que lo llama
    es codigo muerto: nunca se ejecuta, se confirmo probandolo contra un
    conflicto de puerto real. La unica forma confiable de dar un aviso propio
    y claro es probar el puerto por separado, antes de entregarle el control
    a Werkzeug.

    Ademas, un intento de bind sobre un puerto ya tomado en Windows a veces
    da "permiso denegado" (WSAEACCES) en vez de "direccion en uso"
    (WSAEADDRINUSE) -- tambien confirmado en la practica -- asi que aqui no
    se distingue el motivo: cualquier `OSError` al intentar el bind cuenta
    como "no disponible".
    """
    # Sin SO_REUSEADDR a proposito: se quiere saber si el puerto esta
    # LIBRE de verdad, no si se podria reusar un socket ajeno que ya esta
    # escuchando -- eso daria un falso "disponible" en Windows.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, puerto))
        except OSError:
            return False
        return True
