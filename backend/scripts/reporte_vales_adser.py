#!/usr/bin/env python3
"""Reporte de custodia de material sobre los vales migrados de adser
(incident + nm_incident_product). Solo lectura, no modifica nada.

Requiere que fix_adser_close_date_sentinel.py ya haya corrido -- antes de
esa correccion, nm_incident_product.close_date traia el centinela
1990-01-01 para "aun no se cierra", y esta consulta habria mostrado esos
renglones como ya devueltos.

Tres modos:
  --quien-tiene-que          Lo que sigue prestado ahorita, agrupado por persona.
  --por-persona <id_user>    Todo lo que esa persona ha pedido, historico.
  --por-producto <id_product> Quien se ha llevado ese producto, historico.
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


def quien_tiene_que(cur):
    cur.execute("""
        SELECT u.full_name, i.id_incident, p.id_product, p.descripcion,
               nip.quantity, i.incident_date
        FROM nm_incident_product nip
        JOIN incident i ON i.id_incident = nip.id_incident
        JOIN "user" u ON u.id_user = i.id_user
        JOIN product p ON p.id_product = nip.id_product
        WHERE nip.close_date IS NULL AND nip.deletion_date IS NULL
        ORDER BY u.full_name, i.id_incident
    """)
    filas = cur.fetchall()
    print(f"Renglones prestados sin devolver: {len(filas)}\n")
    persona_actual = None
    for nombre, id_incident, id_product, descripcion, cantidad, fecha in filas:
        if nombre != persona_actual:
            print(f"\n{nombre}:")
            persona_actual = nombre
        print(f"  vale {id_incident} · producto {id_product} ({descripcion}) "
              f"x{cantidad} · desde {fecha:%Y-%m-%d}")


def por_persona(cur, id_user: int):
    cur.execute("""
        SELECT i.id_incident, p.id_product, p.descripcion, nip.quantity,
               i.incident_date, nip.close_date
        FROM nm_incident_product nip
        JOIN incident i ON i.id_incident = nip.id_incident
        JOIN product p ON p.id_product = nip.id_product
        WHERE i.id_user = %s AND nip.deletion_date IS NULL
        ORDER BY i.incident_date
    """, (id_user,))
    filas = cur.fetchall()
    print(f"Historial completo de la persona id_user={id_user}: {len(filas)} renglones\n")
    for id_incident, id_product, descripcion, cantidad, fecha_pedido, fecha_cierre in filas:
        estado = "abierto" if fecha_cierre is None else f"devuelto {fecha_cierre:%Y-%m-%d}"
        print(f"  vale {id_incident} · producto {id_product} ({descripcion}) "
              f"x{cantidad} · pedido {fecha_pedido:%Y-%m-%d} · {estado}")


def por_producto(cur, id_product: int):
    cur.execute("""
        SELECT i.id_incident, u.full_name, nip.quantity, i.incident_date,
               nip.close_date
        FROM nm_incident_product nip
        JOIN incident i ON i.id_incident = nip.id_incident
        JOIN "user" u ON u.id_user = i.id_user
        WHERE nip.id_product = %s AND nip.deletion_date IS NULL
        ORDER BY i.incident_date
    """, (id_product,))
    filas = cur.fetchall()
    print(f"Historial completo del producto id_product={id_product}: {len(filas)} renglones\n")
    for id_incident, nombre, cantidad, fecha_pedido, fecha_cierre in filas:
        estado = "abierto" if fecha_cierre is None else f"devuelto {fecha_cierre:%Y-%m-%d}"
        print(f"  vale {id_incident} · {nombre} x{cantidad} · "
              f"pedido {fecha_pedido:%Y-%m-%d} · {estado}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--quien-tiene-que', action='store_true')
    grupo.add_argument('--por-persona', type=int, metavar='ID_USER')
    grupo.add_argument('--por-producto', type=int, metavar='ID_PRODUCT')
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        if args.quien_tiene_que:
            quien_tiene_que(cur)
        elif args.por_persona is not None:
            por_persona(cur, args.por_persona)
        elif args.por_producto is not None:
            por_producto(cur, args.por_producto)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
