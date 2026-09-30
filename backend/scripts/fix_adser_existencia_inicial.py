#!/usr/bin/env python3
"""Corrige la existencia inicial de adser: no cuenta como "en almacen" lo que esta
prestado, destruido o extraviado.

Que paso
--------
Al migrar adser, la existencia de cada producto (`inventory_stock`) nacio igual a su
`cantidad` -en casi todos, 1-, sin mirar donde esta la pieza. Medido 2026-09-29 en
adser-prod (libro vacio, 0 movimientos):

* 178 de los 179 productos con un prestamo vigente cuentan existencia 1 "en almacen"
  aunque estan en manos de alguien;
* los 151 productos destruidos o extraviados (catalogo `retirado` / `extraviado`)
  tambien cuentan 1.

Consecuencias, las dos reales: (1) si alguien devuelve una herramienta prestada, la
existencia sube a 2 -una pieza que nunca estuvo descontada-, que fue justo lo que
dejaron los vales de prueba en tyakxa-dev; y (2) los KPI de existencia
(`articulos_bajo_stock`) y cualquier conteo de almacen se ven inflados en ~330 piezas.

Que hace
--------
Para cada producto FUNGIBLE con existencia, calcula cuanto hay de verdad en almacen:

* si su estado de catalogo es `retirado` o `extraviado`  -> 0;
* si no  -> `cantidad` menos lo que esta prestado (renglones de SALIDA sin cerrar de
  vales que NO son de baja; una baja abierta es una herramienta que ya no esta, y no
  un prestamo), sin bajar de 0.

y solo si la existencia actual es MAYOR, la baja con un movimiento de AJUSTE en el
libro (que es de solo agregado): queda escrito quien, cuando y por que. NUNCA sube una
existencia. Lo `danado` no se toca: no se sabe si esta en almacen.

Solo actua sobre productos SIN movimientos en el libro (la existencia INICIAL): un
producto que ya opero la app tiene una existencia que refleja lo que paso de verdad, y
`cantidad` cambia con cada movimiento, asi que recalcular sobre ella no seria seguro.
Por eso es idempotente: tras corregir, el producto ya tiene un movimiento y no se
vuelve a tocar. `--dry-run` no escribe nada.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2

# Se corre como `python scripts/x.py`, asi que la carpeta del paquete `app` no esta
# en el path por omision.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ADMIN = {"id_user": 1, "id_proyect": 1, "id_permission": 1, "user_type": "admin", "is_superuser": True}
MOTIVO = ("Existencia inicial de la migracion: la pieza no estaba en almacen "
          "(prestada, destruida o extraviada)")
BAJAS = ("destruccion", "destrucción", "extraviado")

SQL_OBJETIVO = """
WITH prestado AS (
    SELECT n.id_product, sum(n.quantity) AS unidades
    FROM nm_incident_product n
    JOIN incident i ON i.id_incident = n.id_incident
    JOIN incident_type t ON t.id_incident_type = i.id_incident_type
    WHERE n.deletion_date IS NULL AND i.deletion_date IS NULL
      AND n.direction = 'salida' AND (n.close_date IS NULL OR n.close_date < '2000-01-01')
      AND lower(trim(t.incident_type_description)) NOT IN %s
    GROUP BY n.id_product
)
SELECT p.id_product, s.id_location, s.quantity AS existencia, p.cantidad,
       coalesce(pr.unidades, 0) AS prestado, st.inventory_status_code AS estado,
       CASE WHEN st.inventory_status_code IN ('retirado', 'extraviado')
                 OR upper(translate(trim(p.product_status), 'Ñ', 'N')) IN ('DESTRUCCION', 'EXTRAVIADO') THEN 0
            ELSE greatest(0, coalesce(p.cantidad, 0) - coalesce(pr.unidades, 0)) END AS objetivo,
       EXISTS (SELECT 1 FROM inventory_ledger l WHERE l.id_product = p.id_product) AS con_movimientos
FROM product p
JOIN inventory_stock s ON s.id_product = p.id_product
LEFT JOIN prestado pr ON pr.id_product = p.id_product
LEFT JOIN inventory_status st ON st.id_inventory_status = p.id_inventory_status
WHERE p.deletion_date IS NULL AND p.tracking_mode = 'fungible'
ORDER BY p.id_product
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
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute(SQL_OBJETIVO, (BAJAS,))
        filas = cur.fetchall()
    finally:
        conn.close()

    # Solo la existencia INICIAL: un producto que ya tiene movimientos en el libro ya
    # lo opero la app, y su existencia refleja lo que paso de verdad. Ademas `cantidad`
    # cambia con cada movimiento, asi que recalcular sobre ella no seria idempotente.
    con_movimientos = [f for f in filas if f[7] and f[2] > f[6]]
    por_corregir = [f for f in filas if f[2] > f[6] and not f[7]]
    prestados = [f for f in por_corregir if f[6] > 0 or f[4] > 0]
    perdidos = [f for f in por_corregir if f not in prestados]
    print(f"productos fungibles con existencia: {len(filas)}")
    print(f"a corregir: {len(por_corregir)} ({len(prestados)} prestados, {len(perdidos)} destruidos o extraviados)")
    print(f"unidades que dejan de contarse como en almacen: {sum(f[2] - f[6] for f in por_corregir)}")
    print(f"omitidos por tener ya movimientos en el libro (su existencia es de la app): {len(con_movimientos)}")
    if args.dry_run:
        print("\n--dry-run: no se escribio nada.")
        return 0

    from app.services.inventory_service import apply_inventory_movement

    hechos = fallidos = 0
    for id_producto, id_ubicacion, existencia, _cantidad, _prestado, _estado, objetivo, _mov in por_corregir:
        delta = objetivo - existencia
        try:
            apply_inventory_movement(id_producto, {
                "movement_type": "adjustment", "quantity_delta": delta, "id_location": id_ubicacion,
                "reason": MOTIVO, "idempotency_key": f"existencia-inicial:{id_producto}:{delta}",
            }, ADMIN)
            hechos += 1
        except Exception as error:  # noqa: BLE001
            fallidos += 1
            print(f"  AVISO producto {id_producto}: {type(error).__name__} {getattr(error, 'message_key', error)}")
    print(f"\najustes aplicados: {hechos}; fallidos: {fallidos}")
    return 0 if fallidos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
