#!/usr/bin/env python3
"""Le asigna el Jefe de taller a los proyectos con maquila que siguen sin supervisor.

Por que existe
--------------
Ya no hay boton de "Tomar proyecto": un proyecto con maquila se le asigna solo al Jefe de
taller cuando hay UNO (`_asignar_jefe_de_taller`, project_management_service.py). Esto pone al
dia lo que se levanto antes, que quedo con `id_supervisor` vacio.

Que toca (y que NO)
-------------------
Solo proyectos vivos con maquila y sin supervisor, y solo si hay exactamente un usuario con la
capacidad `project_execution` y sin `project_authorization` (los roles de administracion
tienen las dos y no son jefes de taller); con cero o varios no hace nada. No toca los que ya tienen
supervisor ni los de proyectos sin maquila.

Uso (dentro del backend del ambiente):
    python scripts/asignar_jefe_de_taller.py --dry-run
    python scripts/asignar_jefe_de_taller.py

Idempotente. El respaldo es la lista que imprime (los ids que cambian vuelven a NULL).
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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id_user, full_name FROM \"user\" WHERE deletion_date IS NULL AND id_permission IN ("
            "SELECT id_permission FROM entity_permission WHERE entity_name = 'project_execution' "
            "AND scope_read > 0 AND deletion_date IS NULL) AND id_permission NOT IN ("
            "SELECT id_permission FROM entity_permission WHERE entity_name = 'project_authorization' "
            "AND scope_read > 0 AND deletion_date IS NULL)")
        jefes = cur.fetchall()
        print(f"jefes de taller (ejecutan y no autorizan): {len(jefes)}")
        if len(jefes) != 1:
            print("no hay exactamente uno: no se asigna nada.")
            return
        id_jefe, nombre = jefes[0]

        cur.execute(
            "SELECT id_proyect, title FROM proyect WHERE deletion_date IS NULL "
            "AND requires_maquila AND id_supervisor IS NULL ORDER BY id_proyect")
        filas = cur.fetchall()
        print(f"proyectos con maquila sin supervisor: {len(filas)} -> {nombre} (#{id_jefe})")
        for id_proyect, titulo in filas:
            print(f"  #{id_proyect}  {titulo or ''}")
        if not filas:
            return

        cur.execute(
            "UPDATE proyect SET id_supervisor = %s WHERE deletion_date IS NULL "
            "AND requires_maquila AND id_supervisor IS NULL", (id_jefe,))
        if args.dry_run:
            conn.rollback()
            print("--dry-run: nada se escribio.")
        else:
            conn.commit()
            print(f"asignados: {cur.rowcount}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
