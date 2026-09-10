#!/usr/bin/env python3
"""Corrige invoice.id_proyect NULL en las 2 facturas de apertura de adser.

migrate_adser.py creo la factura de apertura ("Inventario Existene") sin
fijar id_proyect -- quedo NULL. Efecto real, no solo cosmetico:
inventory_trace_service (la busqueda de producto en Localizar y en el vale
de almacen) oculta cualquier producto cuya factura no coincida con el
id_proyect del usuario que busca -- NULL nunca coincide con nada, asi que
NINGUN usuario no-admin puede ver ni buscar ninguno de los ~2220 productos
migrados de adser. Confirmado real contra adser-prod: los empleados de
almacen (Almacenista, id_permission=5) tienen id_proyect=1, las 2 facturas
NULL.

Se corrige a id_proyect=1 (el proyecto bootstrap "Default Project"), el
mismo criterio que ya se uso para user.id_proyect al migrar los empleados.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

PROYECTO_BOOTSTRAP = 1


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM invoice WHERE id_proyect IS NULL")
        (afectadas,) = cur.fetchone()

        if not args.dry_run:
            cur.execute(
                "UPDATE invoice SET id_proyect = %s WHERE id_proyect IS NULL",
                (PROYECTO_BOOTSTRAP,),
            )
            conn.commit()
            print(f"invoice.id_proyect corregidos: {afectadas}")
        else:
            conn.rollback()
            print(f"[dry-run] invoice.id_proyect a corregir: {afectadas}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
