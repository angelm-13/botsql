#!/usr/bin/env python3
"""Sincroniza devoluciones reales de adser capturadas en el sistema legado
despues del corte de la migracion (2026-09-07), tomadas del respaldo
`Sep2126` (verificado, a diferencia del respaldo del 2026-09-14 que resulto
ser el mismo dataset congelado -- ver memoria de sesion).

Se comparo cada fila de `producto`/`nm_incidente_producto` del respaldo
legado contra lo ya migrado en Postgres (diff completo, no por fecha de
actualizacion -- ese metodo se probo insuficiente, ver hallazgo de la
sesion) y se encontraron exactamente 13 productos + 14 renglones de vale
que el sistema legado ya marca como devueltos/cerrados pero que en el ERP
seguian abiertos. Nada mas cambio: no hay productos, vales ni facturas
nuevas -- es puro estado de "ya regreso", nada de historial se inventa.

Los IDs y fechas de este archivo son los mismos en adser-prod y en
tyakxa-dev (la copia de prueba se migro de los mismos datos originales, con
los mismos IDs preservados). Cada UPDATE trae ademas el estado anterior
esperado como condicion (`product_status='SALIDA'`) para no pisar nada si
el dato ya cambio por otra via.

OJO -- descubierto al probar este script contra tyakxa-dev: ese ambiente
nunca recibio `fix_adser_close_date_sentinel.py` (adser-prod si, en
septiembre). Ahi `close_date` todavia trae el centinela '1990-01-01' en vez
de NULL en estas mismas 14 filas -- por eso "cerrado" se decide con
`close_date IS NULL OR close_date = '1990-01-01'`, no solo IS NULL, para
que este script funcione igual en los dos ambientes. Esa brecha en
tyakxa-dev (451 renglones con el centinela, 65 vales, y ademas
`direction IS NULL` en las 2768 filas migradas -- tampoco recibio
`fix_adser_direction_salida.py`) es un pendiente aparte, no se corrige
aqui.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

SENTINELA = '1990-01-01'

# (id_nm_incident_product, id_incident, id_product, fecha_de_cierre_real)
DEVOLUCIONES = [
    (2731, 130, 2210, '2026-09-15 01:55:07'),
    (2732, 130, 424, '2026-09-15 01:56:28'),
    (2688, 130, 454, '2026-09-15 01:57:08'),
    (2687, 130, 548, '2026-09-15 02:01:18'),
    (2738, 130, 2085, '2026-09-15 02:02:22'),
    (2686, 130, 541, '2026-09-15 02:02:59'),
    (2685, 130, 148, '2026-09-15 02:03:35'),
    (2684, 130, 360, '2026-09-15 02:05:10'),
    (2689, 130, 2180, '2026-09-15 02:06:09'),
    (2690, 130, 217, '2026-09-15 02:06:16'),
    (2692, 130, 1738, '2026-09-15 02:07:13'),
    (2693, 130, 362, '2026-09-15 02:08:55'),
    (2783, 136, 225, '2026-09-15 02:10:01'),
    (2354, 114, 225, '2026-09-15 02:12:34'),
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

    # Ultima fecha real de cierre por producto (225 aparece en 2 vales distintos).
    ultima_fecha_por_producto: dict[int, str] = {}
    for _id_nmip, _id_incident, id_product, fecha in DEVOLUCIONES:
        if id_product not in ultima_fecha_por_producto or fecha > ultima_fecha_por_producto[id_product]:
            ultima_fecha_por_producto[id_product] = fecha

    conn = conectar()
    try:
        cur = conn.cursor()

        renglones_actualizados = 0
        renglones_ya_al_dia = 0
        for id_nmip, id_incident, id_product, fecha in DEVOLUCIONES:
            cur.execute(
                "SELECT close_date FROM nm_incident_product "
                "WHERE id_nm_incident_product = %s AND id_incident = %s AND id_product = %s",
                (id_nmip, id_incident, id_product),
            )
            fila = cur.fetchone()
            if fila is None:
                print(f"  AVISO: no existe id_nm_incident_product={id_nmip} (vale {id_incident}, producto {id_product}) -- se omite")
                continue
            ya_cerrado = fila[0] is not None and str(fila[0]) != f'{SENTINELA} 00:00:00'
            if ya_cerrado:
                renglones_ya_al_dia += 1
                continue
            if not args.dry_run:
                cur.execute(
                    "UPDATE nm_incident_product SET close_date = %s, last_update_date = %s "
                    "WHERE id_nm_incident_product = %s AND (close_date IS NULL OR close_date = %s)",
                    (fecha, fecha, id_nmip, SENTINELA),
                )
            renglones_actualizados += 1

        productos_actualizados = 0
        productos_ya_al_dia = 0
        for id_product, fecha in ultima_fecha_por_producto.items():
            cur.execute("SELECT product_status FROM product WHERE id_product = %s", (id_product,))
            fila = cur.fetchone()
            if fila is None:
                print(f"  AVISO: no existe id_product={id_product} -- se omite")
                continue
            if fila[0] != 'SALIDA':
                productos_ya_al_dia += 1
                continue
            if not args.dry_run:
                cur.execute(
                    "UPDATE product SET product_status = 'ENTRADA', last_update_date = %s "
                    "WHERE id_product = %s AND product_status = 'SALIDA'",
                    (fecha, id_product),
                )
            productos_actualizados += 1

        if not args.dry_run:
            conn.commit()
            print("\nSincronizacion confirmada.")
        else:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")

        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}renglones de vale cerrados: {renglones_actualizados} (ya estaban al dia: {renglones_ya_al_dia})")
        print(f"{prefijo}productos marcados ENTRADA: {productos_actualizados} (ya estaban al dia: {productos_ya_al_dia})")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
