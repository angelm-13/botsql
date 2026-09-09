#!/usr/bin/env python3
"""Rellena nm_incident_product.direction = 'salida' en los renglones que
migrate_adser.py (migrar_nm_incident_product) trajo antes de que existiera
esa columna (migracion 20260904090000_tipo_de_material_y_vale_de_almacen.sql,
que la agrega NULL a proposito, sin inventar un valor para lo que ya
existia).

Por que 'salida' y no otra cosa: antes del rediseno de vale de almacen, el
unico concepto que existia era "un vale saca un producto, con quantity, y
fecha_cierre dice cuando volvio (NULL si sigue afuera)". Eso es exactamente
la semantica de 'salida' en warehouse_voucher_service. No hay 'entrada' ni
'traslado' que inventar: esos son movimientos nuevos, propios del vale
rediseñado, que no existian en el sistema legado.

Sin esta correccion, todas las consultas de "quien tiene que" y "que ha
pedido cada quien" (warehouse_voucher_service.py: vales_vencidos,
vales_de_usuario, historial_de_producto, y el tablero de vencidos) filtran
por `direction == SALIDA` y devuelven vacio para las 2768 filas migradas de
adser, aunque el vale siga realmente abierto segun close_date.

Alcance: SOLO renglones con direction IS NULL. Cualquier renglon capturado
ya con el flujo nuevo (warehouse_voucher_service) trae su direction desde
que se crea, asi que nunca entra aqui. Idempotente: despues de la primera
corrida no queda ningun NULL que volver a tocar.
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

        cur.execute("SELECT count(*) FROM nm_incident_product WHERE direction IS NULL")
        (total,) = cur.fetchone()

        cur.execute(
            "SELECT count(*) FROM nm_incident_product "
            "WHERE direction IS NULL AND close_date IS NULL"
        )
        (abiertos,) = cur.fetchone()

        if not args.dry_run:
            cur.execute(
                "UPDATE nm_incident_product SET direction = 'salida' WHERE direction IS NULL"
            )
            conn.commit()
            print(f"nm_incident_product.direction corregidos: {total}")
            print(f"  de esos, siguen abiertos (close_date IS NULL): {abiertos}")
        else:
            conn.rollback()
            print(f"[dry-run] nm_incident_product.direction a corregir: {total}")
            print(f"[dry-run] de esos, siguen abiertos (close_date IS NULL): {abiertos}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
