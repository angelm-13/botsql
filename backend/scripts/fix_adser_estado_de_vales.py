#!/usr/bin/env python3
"""Deriva el estado de los vales migrados que dicen "abierta" con todos sus renglones
ya cerrados.

Por que
-------
En la app el estado de un vale NO se captura, se DERIVA de sus renglones
(`warehouse_voucher_service._estado_derivado`): queda uno sin cerrar -> abierto; se
cierra el ultimo -> cerrado, con la fecha del ultimo cierre. Es lo que evita "un vale
abierto con todo devuelto".

El sistema anterior si dejaba capturar el estado a mano, y `migrate_adser.py` lo copio
tal cual. Medido 2026-09-29: 14 vales de adser-prod (13 en tyakxa-dev, mas uno que se
suma al cerrar los gemelos) estan "abierta" y no tienen ni un renglon de salida
abierto. Como la app solo re-deriva al devolver un renglon, y aqui ya no queda nada por
devolver, nunca se corregirian solos y siguen apareciendo como vales abiertos.

Alcance
-------
SOLO el caso seguro: vale "abierta" con al menos un renglon de salida y NINGUNO abierto
(`close_date` NULL o el centinela de 1990). Se cierra con la fecha del ultimo cierre de
sus renglones, igual que la app.

NO toca el caso contrario -vale "cerrada" que conserva renglones abiertos-: hay 10 en
adser-prod y 7 son de tipo Destruccion/Dañado/Extraviado, donde el vale cerrado con la
herramienta "abierta" es la forma en que el sistema anterior registraba una baja. Eso
no es una inconsistencia que se derive: es una decision de como contar "quien tiene
que" (ver docs/despliegues/2026-09-29_estado_de_pieza_por_tipo_de_vale.md).

Idempotente. `--dry-run` no escribe nada.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

ABIERTA = ('abierta', 'abierto')
CERRADA = 'cerrada'


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
            "SELECT i.id_incident, max(n.close_date) "
            "FROM incident i JOIN nm_incident_product n "
            "  ON n.id_incident = i.id_incident AND n.deletion_date IS NULL "
            "WHERE i.deletion_date IS NULL AND i.incident_status IN %s "
            "GROUP BY i.id_incident "
            "HAVING count(*) FILTER (WHERE n.direction = 'salida') > 0 "
            "   AND count(*) FILTER (WHERE n.close_date IS NULL OR n.close_date < '2000-01-01') = 0 "
            "ORDER BY i.id_incident",
            (ABIERTA,),
        )
        candidatos = cur.fetchall()

        for id_vale, ultimo in candidatos:
            print(f"  vale {id_vale}: abierta -> cerrada, close_date={ultimo}")
            if not args.dry_run:
                cur.execute(
                    "UPDATE incident SET incident_status = %s, close_date = %s, last_update_date = now() "
                    "WHERE id_incident = %s AND incident_status IN %s",
                    (CERRADA, ultimo, id_vale, ABIERTA),
                )

        if args.dry_run:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")
        else:
            conn.commit()
            print("\nEstados derivados confirmados.")
        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}vales {'a cerrar' if args.dry_run else 'cerrados'} (abierta con todo devuelto): {len(candidatos)}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
