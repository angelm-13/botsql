#!/usr/bin/env python3
"""Quita la partida (`proyect.folio`) que el SISTEMA le puso a un proyecto.

Por que existe
--------------
La partida es una referencia libre de quien captura (opcional, puede repetirse).
Hasta el 2026-10-16 una migracion -`20260918130000`, que se reaplicaba en cada
arranque- le escribia `OT-<anio>-<consecutivo>` a todo proyecto sin partida. Ese
numero nunca lo escribio nadie, asi que se limpia: vuelve a NULL.

Que toca (y que NO)
-------------------
Solo filas vivas cuya partida tenga EXACTAMENTE la forma `OT-AAAA-NNNNN`
(anio de 4 digitos, consecutivo de 5). Una partida capturada a mano con otra
forma ("1", "10130", "1-3", "OT-2026-0042") no se toca. Una persona que
hubiera escrito a mano justo `OT-2026-00001` si coincidiria con el patron:
por eso el script LISTA cada fila (id, titulo, partida, quien lo creo) antes de
cambiar nada, y deja un respaldo en CSV con el valor anterior.

Uso (dentro del backend del ambiente):
    python scripts/limpiar_folios_autogenerados.py --dry-run
    python scripts/limpiar_folios_autogenerados.py --respaldo /tmp/folios_ot.csv

`--dry-run` revierte todo y no escribe el respaldo. Sin `--dry-run` el respaldo
se escribe ANTES de confirmar; si no se puede escribir, no se cambia nada.
Es idempotente: una segunda corrida ya no encuentra nada.

Donde guardar el respaldo: el `/tmp` de un pod se pierde al reiniciar. Pasa
`--respaldo /uploads/folios_ot_AAAA-MM-DD.csv` (la carpeta `/uploads` es un
volumen persistente) o copia el archivo fuera con `kubectl cp` antes de
reiniciar. La lista que imprime el script (id, partida, titulo) tambien sirve
de respaldo: es todo lo que se cambia.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime

import psycopg2

PATRON = r'^OT-[0-9]{4}-[0-9]{5}$'


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
                        help='ruta del CSV con el valor anterior (por omision, uno con fecha en /tmp)')
    args = parser.parse_args()

    ruta = args.respaldo or f"/tmp/folios_ot_respaldo_{datetime.now():%Y%m%d_%H%M%S}.csv"

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id_proyect, folio, title, created_by FROM proyect "
            "WHERE deletion_date IS NULL AND folio ~ %s ORDER BY id_proyect",
            (PATRON,),
        )
        filas = cur.fetchall()
        print(f"proyectos con una partida de la forma OT-AAAA-NNNNN: {len(filas)}")
        for id_proyect, folio, titulo, creado_por in filas:
            print(f"  #{id_proyect}  {folio}  creado_por={creado_por}  {titulo or ''}")

        if not filas:
            print("nada que limpiar.")
            return

        if not args.dry_run:
            with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(['id_proyect', 'folio_anterior', 'title', 'created_by'])
                escritor.writerows(filas)
            print(f"respaldo escrito en {ruta}")

        cur.execute(
            "UPDATE proyect SET folio = NULL, last_update_date = now() "
            "WHERE deletion_date IS NULL AND folio ~ %s",
            (PATRON,),
        )
        cambiadas = cur.rowcount

        if args.dry_run:
            conn.rollback()
            print(f"\n--dry-run: {cambiadas} filas se limpiarian; todo revertido, no se escribio nada.")
        else:
            conn.commit()
            print(f"\nLimpieza confirmada: {cambiadas} filas con la partida vacia.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
