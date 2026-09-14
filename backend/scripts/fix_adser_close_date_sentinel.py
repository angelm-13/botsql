#!/usr/bin/env python3
"""Corrige el centinela 1990-01-01 en close_date, copiado tal cual desde
adser sin la limpieza que si se aplico a product.deletion_date y
usuario.deletion_date (ver artefacto "Mapeo de Migracion - Adser", seccion
04: "El sentinela de baja es 1990-01-01 aqui... sentinela -> NULL, no copiar
la fecha literal").

migrate_adser.py (migrar_nm_incident_product) e (migrar_incident) copiaron
fecha_cierre/close_date tal cual desde MySQL, sin ese mismo tratamiento.
Adser usaba 1990-01-01 tambien ahi para decir "todavia no se cierra" -- no
es una fecha real. Sin esta correccion, dos cosas fallan en produccion:

1. warehouse_voucher_service._estado_derivado() (y consultar_vale, y
   cerrar_renglon) deciden "abierto/cerrado" mirando
   `NmIncidentProduct.close_date IS NULL` -- un centinela no es NULL, asi
   que un prestamo nunca devuelto se lee como "ya cerrado".
2. cerrar_renglon() revienta con "errors.voucher_line_already_closed" si
   alguien intenta cerrar ese renglon de verdad -- el almacen no puede
   cerrar un vale que la app ya cree cerrado.

Corrige ambas tablas por la misma razon: nm_incident_product.close_date (el
dato que de verdad usa la logica de vale) e incident.close_date (nivel-vale,
se autocorregiria solo la proxima vez que se cierre un renglon via
_sincronizar_estado, pero queda incorrecto mientras tanto si algo lo lee
directo).
"""
from __future__ import annotations

import argparse
import os

import psycopg2

SENTINELA = '1990-01-01'


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

        cur.execute(
            "SELECT count(*) FROM nm_incident_product WHERE close_date = %s",
            (SENTINELA,),
        )
        (renglones,) = cur.fetchone()

        cur.execute(
            "SELECT count(*) FROM incident WHERE close_date = %s",
            (SENTINELA,),
        )
        (vales,) = cur.fetchone()

        if not args.dry_run:
            cur.execute(
                "UPDATE nm_incident_product SET close_date = NULL WHERE close_date = %s",
                (SENTINELA,),
            )
            cur.execute(
                "UPDATE incident SET close_date = NULL WHERE close_date = %s",
                (SENTINELA,),
            )
            conn.commit()
            print(f"nm_incident_product.close_date corregidos: {renglones}")
            print(f"incident.close_date corregidos: {vales}")
        else:
            conn.rollback()
            print(f"[dry-run] nm_incident_product.close_date a corregir: {renglones}")
            print(f"[dry-run] incident.close_date a corregir: {vales}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
