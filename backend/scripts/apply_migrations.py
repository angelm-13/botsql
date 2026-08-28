"""Aplica las migraciones pendientes y deja constancia de cuales se aplicaron.

El hallazgo
-----------
Habia 41 archivos de migracion y nada que los ejecutara: ni el arranque del
contenedor ni docker-compose los mencionaban. Se habian corrido a mano, uno por
uno, y no quedaba registro de cuales. Eso deja dos agujeros:

* una instalacion nueva no tiene camino definido desde la base vacia hasta el
  esquema actual; hay que adivinar el orden y confiar en que nadie se salte
  ninguna;
* sobre una base existente nadie puede decir cual falta, asi que la unica forma
  de averiguarlo es intentarlo y ver que revienta.

Como se resuelve
----------------
Una tabla `schema_migration` con el nombre del archivo, cuando se aplico y la
huella de su contenido. Cada migracion corre en su propia transaccion: si falla,
esa queda sin aplicar y sin registrar, y las anteriores se conservan.

La huella importa mas de lo que parece. Editar una migracion ya aplicada es la
forma mas silenciosa de que dos bases diverjan: la que ya la corrio conserva la
version vieja, la nueva aplica la corregida, y nada avisa. Aqui un archivo que
cambio despues de aplicarse detiene el proceso.

Uso
---
    python scripts/apply_migrations.py --dry-run   # que falta, sin tocar nada
    python scripts/apply_migrations.py             # aplicar lo pendiente
    python scripts/apply_migrations.py --baseline  # marcar todo como aplicado

`--baseline` es para bases que ya tienen el esquema al dia pero no el registro,
que es justo el caso al momento de escribir esto: registra sin ejecutar.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import sys


RAIZ = pathlib.Path(__file__).resolve().parents[2]
MIGRACIONES = RAIZ / "database" / "migrations"

CREAR_REGISTRO = """
CREATE TABLE IF NOT EXISTS schema_migration (
    filename    varchar(255) PRIMARY KEY,
    checksum    char(64)     NOT NULL,
    applied_at  timestamp    NOT NULL DEFAULT now(),
    applied_by  varchar(120)
)
"""


def _motor():
    """Conexion a la base, reutilizando la configuracion de la aplicacion."""
    sys.path.insert(0, str(RAIZ / "backend"))
    from sqlalchemy import create_engine

    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL no esta definida. Este script se ejecuta con la misma "
            "configuracion que la aplicacion."
        )
    return create_engine(url, future=True)


def _huella(ruta: pathlib.Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def archivos() -> list[pathlib.Path]:
    """Las migraciones en el orden en que deben aplicarse.

    El nombre empieza con la fecha y hora, asi que el orden alfabetico es el
    cronologico. Es fragil si alguien nombra un archivo a mano, pero es la
    convencion que ya seguian los 41 existentes y cambiarla ahora reordenaria
    migraciones ya aplicadas.
    """
    return sorted(MIGRACIONES.glob("*.sql"))


def aplicadas(conexion) -> dict[str, str]:
    from sqlalchemy import text

    filas = conexion.execute(text("SELECT filename, checksum FROM schema_migration")).all()
    return {fila[0]: fila[1] for fila in filas}


def _revisar_cambios(pendientes_previas: dict[str, str]) -> list[str]:
    """Migraciones ya aplicadas cuyo contenido cambio despues."""
    alteradas = []
    for ruta in archivos():
        registrada = pendientes_previas.get(ruta.name)
        if registrada and registrada != _huella(ruta):
            alteradas.append(ruta.name)
    return alteradas


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--dry-run", action="store_true",
                            help="Muestra lo que falta sin aplicar nada.")
    analizador.add_argument("--baseline", action="store_true",
                            help="Registra todas como aplicadas sin ejecutarlas.")
    opciones = analizador.parse_args()

    from sqlalchemy import text

    motor = _motor()
    with motor.begin() as conexion:
        conexion.execute(text(CREAR_REGISTRO))

    with motor.connect() as conexion:
        ya = aplicadas(conexion)

    alteradas = _revisar_cambios(ya)
    if alteradas:
        print("Estas migraciones ya se aplicaron pero su contenido cambio despues:")
        for nombre in alteradas:
            print(f"  - {nombre}")
        print(
            "\nEditar una migracion aplicada hace que dos bases diverjan sin que\n"
            "nada avise. Revierte el cambio, o escribe una migracion nueva con la\n"
            "correccion."
        )
        return 1

    pendientes = [ruta for ruta in archivos() if ruta.name not in ya]

    if not pendientes:
        print(f"Sin pendientes. {len(ya)} migraciones registradas.")
        return 0

    print(f"Pendientes: {len(pendientes)} de {len(archivos())}")
    for ruta in pendientes:
        print(f"  - {ruta.name}")

    if opciones.dry_run:
        return 0

    actor = os.getenv("USER") or os.getenv("USERNAME") or "desconocido"

    if opciones.baseline:
        with motor.begin() as conexion:
            for ruta in pendientes:
                conexion.execute(
                    text("INSERT INTO schema_migration (filename, checksum, applied_by) "
                         "VALUES (:f, :c, :a) ON CONFLICT (filename) DO NOTHING"),
                    {"f": ruta.name, "c": _huella(ruta), "a": f"{actor} (baseline)"},
                )
        print(f"\nRegistradas {len(pendientes)} sin ejecutar.")
        return 0

    for ruta in pendientes:
        print(f"\naplicando {ruta.name} ...", end=" ", flush=True)
        try:
            # Cada una en su propia transaccion: si falla, las anteriores
            # quedan aplicadas y registradas, y esta no.
            with motor.begin() as conexion:
                conexion.exec_driver_sql(ruta.read_text(encoding="utf-8"))
                conexion.execute(
                    text("INSERT INTO schema_migration (filename, checksum, applied_by) "
                         "VALUES (:f, :c, :a)"),
                    {"f": ruta.name, "c": _huella(ruta), "a": actor},
                )
        except Exception as error:
            print("FALLA")
            print(f"\n{ruta.name} no se aplico:\n  {error}")
            print("\nLas anteriores quedaron aplicadas. Corrige y vuelve a ejecutar.")
            return 1
        print("ok")

    print(f"\n{len(pendientes)} migraciones aplicadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
