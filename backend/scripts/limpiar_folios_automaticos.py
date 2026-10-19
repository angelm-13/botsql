#!/usr/bin/env python3
"""Vacia las partidas `OT-AAAA-NNNNN` que puso solo la migracion
20260918130000 (hoy retirada): la partida es libre y el sistema no inventa
ninguna. Solo toca los ids que se pidan con --ids y solo si su folio sigue
teniendo ese formato; una partida capturada a mano no se toca.

Respaldo: antes de escribir deja un CSV con (id_proyect, folio) en --respaldo.
--dry-run muestra lo que haria y no escribe nada.
"""
from __future__ import annotations

import argparse
import csv
import os
import re

import psycopg2

AUTOMATICO = re.compile(r'^OT-\d{4}-\d{5}$')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', required=True, help='ids de proyecto separados por coma, ej. 7')
    parser.add_argument('--respaldo', default='respaldo_folios.csv')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    ids = [int(i) for i in args.ids.split(',') if i.strip()]

    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'), port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_proyect, folio FROM proyect WHERE id_proyect = ANY(%s) ORDER BY 1", (ids,))
        filas = cur.fetchall()
        a_limpiar = [(i, f) for i, f in filas if f and AUTOMATICO.match(f)]
        for i, f in filas:
            print(f"  proyecto {i}: {f!r} -> {'se vacia' if (i, f) in a_limpiar else 'se deja'}")
        if args.dry_run or not a_limpiar:
            conn.rollback()
            print("dry-run: no se escribio nada." if args.dry_run else "Nada que limpiar.")
            return
        with open(args.respaldo, 'w', newline='', encoding='utf-8') as fh:
            csv.writer(fh).writerows([('id_proyect', 'folio'), *a_limpiar])
        cur.execute("UPDATE proyect SET folio = NULL, last_update_date = now() WHERE id_proyect = ANY(%s)",
                    ([i for i, _ in a_limpiar],))
        conn.commit()
        print(f"{len(a_limpiar)} partida(s) vaciada(s); respaldo en {args.respaldo}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
