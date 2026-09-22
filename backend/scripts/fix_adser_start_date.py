#!/usr/bin/env python3
"""Rellena nm_incident_product.start_date en los renglones que
migrate_adser.py (migrar_nm_incident_product) trajo sin ese campo -- el
origen (nm_incidente_producto) nunca tuvo una fecha de prestamo por
RENGLON, solo `incidente.fecha_incidente` a nivel de VALE. Eso es lo mismo
que ya hace el reporte del sistema legado: la misma "Fecha prestamo" se
repite en todos los renglones de un mismo vale.

Sin esto, la columna "Cuando" del historial de un empleado
(EmployeeVoucherHistory / documento_del_historial_de_persona) sale en
blanco para cualquier renglon migrado, aunque el vale si tenga fecha.

Alcance: SOLO renglones con start_date IS NULL, tomando
incident.incident_date de su propio vale. Cualquier renglon capturado ya con
el flujo nuevo trae su start_date desde que se crea (crear_vale), asi que
nunca entra aqui. Idempotente: despues de la primera corrida no queda ningun
NULL que volver a tocar.
"""
from __future__ import annotations

import argparse
import os

import psycopg2


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
            "SELECT count(*) FROM nm_incident_product nip "
            "JOIN incident i ON i.id_incident = nip.id_incident "
            "WHERE nip.start_date IS NULL"
        )
        (total,) = cur.fetchone()

        cur.execute(
            "SELECT count(*) FROM nm_incident_product nip "
            "JOIN incident i ON i.id_incident = nip.id_incident "
            "WHERE nip.start_date IS NULL AND i.incident_date IS NULL"
        )
        (sin_fecha_de_vale,) = cur.fetchone()

        if not args.dry_run:
            cur.execute(
                "UPDATE nm_incident_product SET start_date = incident.incident_date "
                "FROM incident WHERE incident.id_incident = nm_incident_product.id_incident "
                "AND nm_incident_product.start_date IS NULL"
            )
            conn.commit()
            print(f"nm_incident_product.start_date corregidos: {total}")
            print(f"  de esos, el vale tampoco tenia incident_date (siguen NULL): {sin_fecha_de_vale}")
        else:
            conn.rollback()
            print(f"[dry-run] nm_incident_product.start_date a corregir: {total}")
            print(f"[dry-run] de esos, el vale tampoco tenia incident_date (seguirian NULL): {sin_fecha_de_vale}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
