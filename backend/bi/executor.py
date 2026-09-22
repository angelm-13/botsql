"""Ejecucion de solo lectura y serializacion a JSON.

Dos trabajos, y ninguno es obvio del todo.

**Ejecutar acotado.** La transaccion se abre de solo lectura y con reloj,
usando la instruccion propia de cada motor. El tope de filas se aplica con
`fetchmany`, no confiando en el `LIMIT` del texto: es la unica garantia que
funciona igual en SQL Server, en Oracle y en un motor que ni siquiera soporte
LIMIT. Dicho de frente: acotar al traer no impide que el servidor calcule el
resultado completo -- de eso se encarga el reloj.

**Serializar sin sorpresas.** `jsonify` de Flask no sabe convertir un
`Decimal`, y un `NUMERIC` de PostgreSQL llega como `Decimal` siempre. Una
suma de dinero -- el dato mas comun de un tablero de BI -- revienta el
endpoint si no se convierte. Lo mismo `date`, `UUID`, `bytes` y los `float`
no finitos, que JSON no puede representar y que `json.dumps` escribe como
`NaN`, produciendo un documento que el navegador rechaza.

Las filas salen como lista de objetos (`[{"mes": "2026-01", "total": 120}]`)
y no como lista de listas: es lo que consumen directo Recharts y Chart.js,
sin que el frontend tenga que cruzar indices con nombres de columna.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time as hora, timedelta
from decimal import Decimal

from sqlalchemy import text

from bi.schema_extractor import acotar_tiempo


@dataclass
class Resultado:
    columnas: tuple[str, ...] = ()
    filas: list[dict] = field(default_factory=list)
    total_filas: int = 0
    truncado: bool = False
    ms: int = 0

    def a_dict(self) -> dict:
        return {
            "columnas": list(self.columnas),
            "filas": self.filas,
            "total_filas": self.total_filas,
            "truncado": self.truncado,
            "ms": self.ms,
        }


# ---------------------------------------------------------------------------
# Serializacion
# ---------------------------------------------------------------------------

def valor_json(v):
    """Un valor que `json.dumps` sabe escribir y el navegador sabe leer."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        # NaN e Infinity no existen en JSON. `json.dumps` los escribe de
        # todas formas y el `JSON.parse` del navegador falla al leerlos.
        return v if math.isfinite(v) else None
    if isinstance(v, Decimal):
        # A float, no a cadena: el frontend tiene que poder graficarlo sin
        # convertir. Se pierde precision mas alla de 2^53, que para un
        # agregado de negocio no ocurre.
        return float(v) if v.is_finite() else None
    if isinstance(v, (datetime, date, hora)):
        return v.isoformat()
    if isinstance(v, timedelta):
        return v.total_seconds()
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, (bytes, bytearray)):
        return f"0x{bytes(v)[:32].hex()}"
    return str(v)


def nombres_unicos(columnas) -> tuple[str, ...]:
    """Nombres de columna sin repetir.

    `SELECT a.id, b.id FROM ...` devuelve dos columnas llamadas `id`. Como
    cada fila es un objeto, la segunda pisaria a la primera en silencio y el
    usuario veria un dato equivocado sin ninguna senal.
    """
    vistos: dict[str, int] = {}
    salida: list[str] = []
    for i, bruto in enumerate(columnas):
        nombre = str(bruto) if bruto else f"columna_{i + 1}"
        if nombre in vistos:
            vistos[nombre] += 1
            nombre = f"{nombre}_{vistos[nombre]}"
        else:
            vistos[nombre] = 1
        salida.append(nombre)
    return tuple(salida)


# ---------------------------------------------------------------------------
# Ejecucion
# ---------------------------------------------------------------------------

def _poner_solo_lectura(con, dialecto: str) -> None:
    """La transaccion no puede escribir, lo diga el SQL o no.

    Es la tercera barrera: aunque el validador tuviera un hueco, el motor
    rechaza cualquier escritura. En SQLite `query_only` es lo equivalente.
    """
    try:
        if dialecto == "postgresql":
            con.exec_driver_sql("SET TRANSACTION READ ONLY")
        elif dialecto in ("mysql", "mariadb"):
            con.exec_driver_sql("SET TRANSACTION READ ONLY")
        elif dialecto == "sqlite":
            con.exec_driver_sql("PRAGMA query_only = ON")
    except Exception:
        # Un motor que no lo soporta (SQL Server no tiene equivalente directo)
        # no debe impedir la consulta: quedan el validador, el rol de solo
        # lectura de la base y el reloj.
        pass


def ejecutar(engine, validado, *, ajustes, gancho=None) -> Resultado:
    """Corre el SQL ya validado y devuelve filas listas para el frontend.

    `gancho` es el punto de extension que hace utilizable este modulo dentro
    de una aplicacion multiinquilino: recibe la conexion antes de la consulta
    y puede fijar ahi el alcance del usuario (por ejemplo
    `SET LOCAL app.id_tenant = ...`, que las vistas leen con
    `current_setting`). El SQL que escribio el modelo no lo puede ver ni
    cambiar.
    """
    dialecto = engine.dialect.name
    inicio = time.monotonic()

    with engine.connect() as con:
        with con.begin():
            _poner_solo_lectura(con, dialecto)
            acotar_tiempo(con, dialecto, ajustes.timeout_sql_ms)
            if gancho is not None:
                gancho(con)

            cursor = con.execute(text(validado.sql))
            columnas = nombres_unicos(cursor.keys())

            # Se pide una fila mas que el tope para poder decir con certeza
            # si el resultado venia cortado, en vez de adivinarlo.
            crudas = cursor.fetchmany(ajustes.limite_filas + 1)

    truncado = len(crudas) > ajustes.limite_filas
    crudas = crudas[: ajustes.limite_filas]

    filas = [
        {columnas[i]: valor_json(v) for i, v in enumerate(fila)}
        for fila in crudas
    ]

    return Resultado(
        columnas=columnas,
        filas=filas,
        total_filas=len(filas),
        truncado=truncado,
        ms=int((time.monotonic() - inicio) * 1000),
    )
