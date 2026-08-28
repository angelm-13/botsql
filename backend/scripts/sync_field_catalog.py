"""Puebla el catalogo `field` a partir de los modelos.

Para que un rol pueda capturar en las pantallas genericas hacen falta dos
cosas: que el campo exista en el catalogo `field`, y que el rol tenga permiso
sobre ese campo en `nm_field_permission`. Sin lo primero, lo segundo no se
puede ni conceder.

El catalogo estaba poblado solo con nueve tablas de logistica. El script
`database/sync_fields.sql` deberia llenarlo, pero apunta a un esquema mas rico
del que existe aqui -declara columnas como `data_type` que la tabla no tiene-,
asi que abortaba en su primera sentencia y, al ir todo dentro de una sola
transaccion, no insertaba nada.

Aqui la fuente son los modelos, que es lo unico que siempre coincide con las
tablas reales. Es idempotente: se puede correr en cada despliegue.

    python scripts/sync_field_catalog.py            # aplica
    python scripts/sync_field_catalog.py --dry-run  # solo informa
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("TESTING", "0")

from sqlalchemy import select  # noqa: E402

import app.models  # noqa: F401,E402  (registra todos los modelos)
from app.models.base import Base  # noqa: E402
from app.models.field import Field  # noqa: E402
from app.models.session import transaction_context  # noqa: E402


# Columnas que el sistema administra solo. No se publican como campos
# configurables porque nadie debe capturarlas a mano.
COLUMNAS_DE_SISTEMA = {"creation_date", "last_update_date", "deletion_date"}


def columnas_publicables():
    """(tabla, columna) de todo lo que tiene sentido exponer."""
    for tabla in Base.metadata.tables.values():
        for columna in tabla.columns:
            if columna.name in COLUMNAS_DE_SISTEMA:
                continue
            yield tabla.name, columna.name


def sincronizar(dry_run=False, actor_id=1) -> dict:
    esperadas = set(columnas_publicables())
    with transaction_context() as db:
        existentes = {
            (fila.table_name, fila.field_name)
            for fila in db.scalars(select(Field)).all()
        }
        faltantes = sorted(esperadas - existentes)
        if not dry_run:
            for tabla, columna in faltantes:
                db.add(Field(table_name=tabla, field_name=columna, created_by=actor_id))
            db.flush()
        return {
            "esperadas": len(esperadas),
            "existentes": len(existentes),
            "agregadas": len(faltantes),
            "tablas_nuevas": sorted({tabla for tabla, _ in faltantes}),
        }


def main():
    parser = argparse.ArgumentParser(description="Sincroniza el catalogo de campos con los modelos.")
    parser.add_argument("--dry-run", action="store_true", help="Informa sin escribir.")
    parser.add_argument("--actor", type=int, default=1, help="Usuario al que se atribuye el alta.")
    args = parser.parse_args()

    resultado = sincronizar(dry_run=args.dry_run, actor_id=args.actor)
    print(f"campos esperados por los modelos : {resultado['esperadas']}")
    print(f"campos ya registrados            : {resultado['existentes']}")
    print(f"campos {'que faltarian' if args.dry_run else 'agregados'}      : {resultado['agregadas']}")
    if resultado["tablas_nuevas"]:
        print(f"tablas cubiertas ahora          : {len(resultado['tablas_nuevas'])}")


if __name__ == "__main__":
    main()
