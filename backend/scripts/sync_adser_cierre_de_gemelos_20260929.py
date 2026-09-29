#!/usr/bin/env python3
"""Cierra en tyakxa-dev los 66 renglones de vale que adser-prod ya tiene cerrados
y el sistema anterior tiene abiertos.

De donde sale
-------------
Al comparar adser-prod contra el respaldo Sep2126 del sistema anterior aparecieron
66 renglones (10 vales) que el sistema anterior tiene ABIERTOS y adser-prod tiene
CERRADOS con fecha real. Nadie dejo escrito el criterio ni el script; este archivo
lo deja escrito, con lo que se pudo comprobar:

* Los 66 tienen un renglon GEMELO -mismo vale, mismo producto, misma cantidad-
  que el sistema anterior SI cerro, y la fecha de cierre aplicada es la del gemelo:
  coincide en 66 de 66 (y es la MINIMA de las fechas de cierre cuando hay varios
  gemelos). El sistema anterior, al devolverse una herramienta, cerraba UNA de las
  copias del bloque guardado varias veces y dejaba las demas "abiertas".
* 57 de los 66 tienen su producto en ENTRADA (devuelto) en el sistema anterior.

Lo que NO esta claro: adser-prod dejo fuera 6 renglones que cumplen lo mismo -los
vales 9 y 19 (producto DAÑADO) y 112 (producto aun en SALIDA)-, y no se sabe por
que. Este script NO los toca y NO generaliza la regla: aplica exactamente los 66
que adser-prod ya tiene, para que dev refleje a prod. Los 6 quedan como decision.

Idempotente y sin efecto en adser-prod, donde ya estan cerrados. Solo toca renglones
vivos, de esa salida, que sigan abiertos (close_date NULL o el centinela de 1990).
NO toca el estado de los vales: de eso se ocupa `fix_adser_estado_de_vales.py`,
que corre despues.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

SENTINELA = '1990-01-01'

# (id_nm_incident_product, id_incident, id_product, close_date aplicada en adser-prod)
CIERRES = [
    (287, 13, 623, "2025-12-06 12:34:43"),
    (576, 27, 2049, "2026-07-29 11:53:19"),
    (1391, 45, 196, "2026-08-06 10:48:15"),
    (984, 50, 370, "2026-05-07 15:10:37"),
    (987, 50, 2074, "2026-04-15 11:21:44"),
    (1493, 75, 783, "2026-07-31 08:00:35"),
    (2048, 95, 2277, "2026-04-01 08:41:09"),
    (2078, 95, 2308, "2026-05-14 12:40:58"),
    (2079, 95, 2307, "2026-05-14 12:41:31"),
    (2252, 112, 2258, "2026-07-25 09:53:07"),
    (2254, 112, 199, "2026-06-24 10:57:43"),
    (2264, 112, 336, "2026-07-03 10:54:54"),
    (2265, 112, 336, "2026-07-03 10:54:54"),
    (2274, 112, 336, "2026-07-03 10:54:54"),
    (2275, 112, 336, "2026-07-03 10:54:54"),
    (2284, 112, 336, "2026-07-03 10:54:54"),
    (2285, 112, 336, "2026-07-03 10:54:54"),
    (2293, 112, 336, "2026-07-03 10:54:54"),
    (2380, 113, 198, "2026-07-03 10:42:33"),
    (2381, 113, 2310, "2026-07-03 10:43:31"),
    (2382, 113, 2313, "2026-07-03 10:44:24"),
    (2383, 113, 2304, "2026-07-03 10:47:17"),
    (2384, 113, 1305, "2026-07-03 10:48:36"),
    (2385, 113, 2312, "2026-07-03 10:49:03"),
    (2386, 113, 2303, "2026-07-03 10:49:32"),
    (2388, 113, 2211, "2026-07-03 10:49:55"),
    (2389, 113, 2307, "2026-06-30 16:52:54"),
    (2390, 113, 2308, "2026-07-03 10:50:21"),
    (2392, 113, 198, "2026-07-03 10:42:33"),
    (2393, 113, 2310, "2026-07-03 10:43:31"),
    (2394, 113, 2313, "2026-07-03 10:44:24"),
    (2395, 113, 2304, "2026-07-03 10:47:17"),
    (2396, 113, 1305, "2026-07-03 10:48:36"),
    (2397, 113, 2312, "2026-07-03 10:49:03"),
    (2398, 113, 2303, "2026-07-03 10:49:32"),
    (2400, 113, 2211, "2026-07-03 10:49:55"),
    (2401, 113, 2307, "2026-06-30 16:52:54"),
    (2402, 113, 2308, "2026-07-03 10:50:21"),
    (2404, 113, 198, "2026-07-03 10:42:33"),
    (2405, 113, 2310, "2026-07-03 10:43:31"),
    (2406, 113, 2313, "2026-07-03 10:44:24"),
    (2407, 113, 2304, "2026-07-03 10:47:17"),
    (2408, 113, 1305, "2026-07-03 10:48:36"),
    (2409, 113, 2312, "2026-07-03 10:49:03"),
    (2410, 113, 2303, "2026-07-03 10:49:32"),
    (2412, 113, 2211, "2026-07-03 10:49:55"),
    (2413, 113, 2307, "2026-06-30 16:52:54"),
    (2414, 113, 2308, "2026-07-03 10:50:21"),
    (2317, 114, 281, "2026-06-25 10:24:35"),
    (2319, 114, 972, "2026-06-25 10:25:47"),
    (2320, 114, 983, "2026-06-25 10:26:01"),
    (2321, 114, 985, "2026-06-25 10:26:20"),
    (2322, 114, 577, "2026-06-25 10:26:43"),
    (2323, 114, 2355, "2026-06-25 10:26:53"),
    (2324, 114, 645, "2026-06-25 10:27:24"),
    (2325, 114, 2409, "2026-06-25 10:27:34"),
    (2326, 114, 281, "2026-06-25 10:24:35"),
    (2328, 114, 972, "2026-06-25 10:25:47"),
    (2329, 114, 983, "2026-06-25 10:26:01"),
    (2330, 114, 985, "2026-06-25 10:26:20"),
    (2331, 114, 577, "2026-06-25 10:26:43"),
    (2332, 114, 2355, "2026-06-25 10:26:53"),
    (2333, 114, 645, "2026-06-25 10:27:24"),
    (2334, 114, 2409, "2026-06-25 10:27:34"),
    (2450, 116, 577, "2026-07-08 16:27:17"),
    (2451, 116, 614, "2026-07-18 10:14:28"),
]


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
        cerrados = ya_cerrados = no_coincide = 0
        for id_linea, id_vale, id_producto, fecha in CIERRES:
            cur.execute(
                "SELECT id_incident, id_product, direction, close_date, deletion_date "
                "FROM nm_incident_product WHERE id_nm_incident_product = %s",
                (id_linea,),
            )
            fila = cur.fetchone()
            if fila is None or fila[0] != id_vale or fila[1] != id_producto or fila[2] != 'salida' or fila[4] is not None:
                no_coincide += 1
                print(f"  AVISO: el renglon {id_linea} no es el esperado (vale {id_vale}, producto {id_producto}) -- se omite")
                continue
            if fila[3] is not None and str(fila[3]) >= '2000-01-01':
                ya_cerrados += 1
                continue
            cur.execute(
                "UPDATE nm_incident_product SET close_date = %s, last_update_date = now() "
                "WHERE id_nm_incident_product = %s AND (close_date IS NULL OR close_date < '2000-01-01')",
                (fecha, id_linea),
            )
            cerrados += cur.rowcount

        if args.dry_run:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")
        else:
            conn.commit()
            print("\nCierres confirmados.")
        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}renglones cerrados: {cerrados}")
        print(f"{prefijo}renglones que ya estaban cerrados: {ya_cerrados}")
        print(f"{prefijo}renglones que no coinciden con lo esperado (omitidos): {no_coincide}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
