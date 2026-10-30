#!/usr/bin/env python3
"""Baja el texto `SALIDA` de productos que ya no tienen nada fuera.

Por que existe
--------------
El sistema anterior escribia `product.product_status = 'SALIDA'` al prestar y
'ENTRADA' al volver. Lo migrado trajo ese texto, y las devoluciones hechas aqui
solo mueven la existencia: el producto seguia diciendo "Salio del almacen" con
todas sus salidas cerradas y la existencia de vuelta en su sitio (123 en
adser-prod al 2026-10-16, entre ellos ROT201 del vale #128).

Desde ese dia `devolver_renglon` baja el texto al cerrar la ultima salida
(`_bajar_salida_obsoleta`) y Localizar lo corrige al pintar (`estatus_efectivo`).
Este script arregla lo que ya estaba asi, para que Inventario y Productos, que
leen el texto crudo, coincidan con Localizar.

Que toca (y que NO)
-------------------
Solo productos vivos con el texto EXACTO `SALIDA` (sin importar mayusculas ni
espacios) que ademas:
  - no tienen ninguna salida abierta de un vale vivo y que no sea una baja
    (misma regla que `_prestado_en_lote`), y
  - tienen existencia en el almacen (`inventory_stock.quantity > 0`).
Pasan a `ENTRADA`. Dañado, extraviado, destruccion y reparacion no se tocan; un
producto con algo fuera (caso mixto) tampoco; uno sin existencia ni salidas
tampoco (no hay de donde concluir nada).

Uso (dentro del backend del ambiente):
    python scripts/limpiar_salida_obsoleta_de_productos.py --dry-run
    python scripts/limpiar_salida_obsoleta_de_productos.py --respaldo /uploads/salida_obsoleta_AAAA-MM-DD.csv

`--dry-run` revierte todo y no escribe el respaldo. Sin `--dry-run` el respaldo
(id y texto anterior) se escribe ANTES de confirmar; si no se puede escribir, no
se cambia nada. Idempotente: una segunda corrida ya no encuentra nada.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime

import psycopg2

SELECCION = """
FROM product p
WHERE p.deletion_date IS NULL
  AND upper(btrim(p.product_status)) = 'SALIDA'
  AND EXISTS (
      SELECT 1 FROM inventory_stock s
      WHERE s.id_product = p.id_product AND s.quantity > 0)
  AND NOT EXISTS (
      SELECT 1
      FROM nm_incident_product n
      JOIN incident i ON i.id_incident = n.id_incident
      WHERE n.id_product = p.id_product
        AND n.direction = 'salida'
        AND n.close_date IS NULL
        AND n.deletion_date IS NULL
        AND i.deletion_date IS NULL
        AND coalesce(lower(i.incident_status), '') NOT IN ('borrador', 'en_espera', 'cancelado')
        AND n.id_incident NOT IN (
            SELECT i2.id_incident
            FROM incident i2
            JOIN incident_type t ON t.id_incident_type = i2.id_incident_type
            WHERE lower(btrim(t.incident_type_description))
                  IN ('destruccion', 'destrucción', 'extraviado')))
"""


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--respaldo', default=None,
                        help='ruta del CSV con el texto anterior (por omision, uno con fecha en /tmp)')
    args = parser.parse_args()

    ruta = args.respaldo or f"/tmp/salida_obsoleta_respaldo_{datetime.now():%Y%m%d_%H%M%S}.csv"

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id_product, p.product_code, p.product_status " + SELECCION
            + " ORDER BY p.id_product")
        filas = cur.fetchall()
        print(f"productos con SALIDA y nada fuera: {len(filas)}")
        for id_producto, codigo, texto in filas:
            print(f"  #{id_producto}  {codigo or ''}  {texto!r}")

        if not filas:
            print("nada que limpiar.")
            return

        if not args.dry_run:
            with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(['id_product', 'product_code', 'product_status_anterior'])
                escritor.writerows(filas)
            print(f"respaldo escrito en {ruta}")

        cur.execute(
            "UPDATE product SET product_status = 'ENTRADA', last_update_date = now() "
            "WHERE id_product IN (SELECT p.id_product " + SELECCION + ")")
        cambiadas = cur.rowcount

        if args.dry_run:
            conn.rollback()
            print(f"\n--dry-run: {cambiadas} filas se corregirian; todo revertido, no se escribio nada.")
        else:
            conn.commit()
            print(f"\nCorreccion confirmada: {cambiadas} productos pasan a ENTRADA.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
