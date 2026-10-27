#!/usr/bin/env python3
"""Unifica dos usuarios duplicados: pasa todo lo que cuelga del usuario
`--origen` al usuario `--destino` y elimina la fila del origen.

Caso real (adser-prod, 2026-10-26): "GIOVANNI MOLINA" (id 42, migrado del
sistema anterior, con su historial de vales) y "Govanny" (id 75, alta por error
el 2026-09-28, con 3 proyectos y avisos). Se conserva el 42.

Que mueve: toda columna con llave foranea a `user.id_user` (se descubren en
cada corrida, no hay lista fija) mas las columnas de usuario sin llave foranea
conocidas (`EXTRA_SIN_FK`). Los datos personales del origen NO pisan los del
destino; solo se avisa de las diferencias para decidir a mano.

Seguridad (reglas de trabajo del repo):
- Simula por omision; con `--aplicar` escribe, todo en UNA transaccion.
- Antes de escribir deja un respaldo JSON (fila completa del origen y las
  llaves primarias de cada fila tocada), suficiente para revertir.
- Se niega a seguir si el movimiento chocaria con una restriccion unica
  (p. ej. el mismo usuario ya esta en el mismo equipo) o si el origen todavia
  tiene referencias que el script no sabe mover.
- Idempotente: una segunda corrida ya no encuentra nada que mover.

Uso (dentro del pod de backend, con DB_* en el entorno):
    python unificar_usuarios.py --origen 75 --destino 42            # simulacion
    python unificar_usuarios.py --origen 75 --destino 42 --aplicar
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import psycopg2

# Columnas que guardan un id de usuario pero no declaran llave foranea.
EXTRA_SIN_FK = [('incident', 'delivered_to_user')]


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def columnas_que_apuntan_a_user(cur):
    cur.execute(
        """
        SELECT cl.relname, a.attname
        FROM pg_constraint k
        JOIN pg_class cl ON cl.oid = k.conrelid
        JOIN pg_namespace ns ON ns.oid = cl.relnamespace AND ns.nspname = 'public'
        JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum = k.conkey[1]
        WHERE k.contype = 'f' AND k.confrelid = 'public."user"'::regclass
          AND array_length(k.conkey, 1) = 1
        ORDER BY 1, 2
        """
    )
    encontradas = [tuple(r) for r in cur.fetchall()]
    for extra in EXTRA_SIN_FK:
        if extra not in encontradas:
            encontradas.append(extra)
    # La propia fila del usuario no se trata como referencia.
    return [c for c in encontradas if c != ('user', 'id_user')]


def llave_primaria(cur, tabla):
    cur.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
        ORDER BY array_position(i.indkey::int[], a.attnum::int)
        """,
        (f'public."{tabla}"',),
    )
    return [r[0] for r in cur.fetchall()]


def choques_unicos(cur, tabla, columna, origen, destino):
    """Filas del origen que, al moverse, repetirian una restriccion unica."""
    cur.execute(
        """
        SELECT k.conname, k.conkey, k.conrelid
        FROM pg_constraint k
        WHERE k.contype = 'u' AND k.conrelid = %s::regclass
        """,
        (f'public."{tabla}"',),
    )
    problemas = []
    for nombre, conkey, relid in cur.fetchall():
        cur.execute(
            "SELECT attname FROM pg_attribute WHERE attrelid = %s AND attnum = ANY(%s)",
            (relid, conkey),
        )
        cols = [r[0] for r in cur.fetchall()]
        if columna not in cols:
            continue
        otras = [c for c in cols if c != columna]
        cond = ' AND '.join(f'o."{c}" IS NOT DISTINCT FROM d."{c}"' for c in otras) or 'TRUE'
        cur.execute(
            f'SELECT count(*) FROM "{tabla}" o JOIN "{tabla}" d ON {cond} '
            f'WHERE o."{columna}" = %s AND d."{columna}" = %s',
            (origen, destino),
        )
        if cur.fetchone()[0]:
            problemas.append(nombre)
    return problemas


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--origen', type=int, required=True, help='usuario que desaparece')
    parser.add_argument('--destino', type=int, required=True, help='usuario que se conserva')
    parser.add_argument('--aplicar', action='store_true', help='escribe (por omision solo simula)')
    parser.add_argument('--respaldo-dir', default='.', help='carpeta donde dejar el respaldo JSON')
    args = parser.parse_args()
    if args.origen == args.destino:
        sys.exit('origen y destino son el mismo usuario')

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM "user" WHERE id_user IN (%s, %s)', (args.origen, args.destino))
        columnas = [d[0] for d in cur.description]
        filas = {r[0]: dict(zip(columnas, r)) for r in cur.fetchall()}
        for uid in (args.origen, args.destino):
            if uid not in filas:
                sys.exit(f'No existe el usuario {uid}')
        origen, destino = filas[args.origen], filas[args.destino]
        if destino['deletion_date'] is not None:
            sys.exit('El usuario destino esta dado de baja; no se unifica hacia el')
        print(f"Origen : {origen['id_user']} {origen['username']!r} ({origen['full_name']!r})")
        print(f"Destino: {destino['id_user']} {destino['username']!r} ({destino['full_name']!r})")

        ignorar = {'id_user', 'username', 'full_name', 'password', 'creation_date', 'last_update_date',
                   'is_employee', 'user_type', 'accepts_marketing', 'title'}
        for c in columnas:
            if c in ignorar:
                continue
            if origen[c] is not None and origen[c] != destino[c]:
                print(f'  AVISO dato personal solo/distinto en el origen: {c} = {origen[c]!r} (destino {destino[c]!r}); no se copia')

        plan = []  # (tabla, columna, pk, [pks])
        choques = []
        for tabla, columna in columnas_que_apuntan_a_user(cur):
            pk = llave_primaria(cur, tabla)
            cur.execute(f'SELECT count(*) FROM "{tabla}" WHERE "{columna}" = %s', (args.origen,))
            n = cur.fetchone()[0]
            if not n:
                continue
            if not pk:
                sys.exit(f'{tabla} no tiene llave primaria: no se puede respaldar con seguridad')
            cur.execute(f'SELECT {", ".join(chr(34) + p + chr(34) for p in pk)} FROM "{tabla}" WHERE "{columna}" = %s ORDER BY 1', (args.origen,))
            plan.append((tabla, columna, pk, [list(r) for r in cur.fetchall()]))
            for nombre in choques_unicos(cur, tabla, columna, args.origen, args.destino):
                choques.append(f'{tabla}.{nombre}')

        if not plan:
            print('Nada que mover: el origen ya no tiene referencias.')
        for tabla, columna, _pk, pks in plan:
            print(f'  {tabla}.{columna}: {len(pks)} fila(s) pasan del {args.origen} al {args.destino}')
        if choques:
            sys.exit('Se detiene: el movimiento repetiria restricciones unicas: ' + ', '.join(choques))

        if not args.aplicar:
            print('\nSIMULACION: no se escribio nada. Repetir con --aplicar.')
            return

        os.makedirs(args.respaldo_dir, exist_ok=True)
        marca = datetime.now().strftime('%Y%m%d_%H%M%S')
        ruta = os.path.join(args.respaldo_dir, f'respaldo_unificar_usuarios_{args.origen}_a_{args.destino}_{marca}.json')
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump({
                'origen': args.origen, 'destino': args.destino, 'fila_origen': origen,
                'movimientos': [{'tabla': t, 'columna': c, 'pk': pk, 'filas': pks} for t, c, pk, pks in plan],
            }, f, default=str, ensure_ascii=False, indent=1)
        print(f'Respaldo: {ruta}')

        for tabla, columna, _pk, pks in plan:
            cur.execute(f'UPDATE "{tabla}" SET "{columna}" = %s WHERE "{columna}" = %s', (args.destino, args.origen))
            if cur.rowcount != len(pks):
                raise RuntimeError(f'{tabla}.{columna}: se esperaban {len(pks)} filas y se movieron {cur.rowcount}')

        # Nada debe seguir apuntando al origen (la llave foranea lo impediria, pero las
        # columnas sin llave foranea no).
        for tabla, columna in columnas_que_apuntan_a_user(cur):
            cur.execute(f'SELECT count(*) FROM "{tabla}" WHERE "{columna}" = %s', (args.origen,))
            if cur.fetchone()[0]:
                raise RuntimeError(f'{tabla}.{columna} sigue apuntando al origen')

        cur.execute('DELETE FROM "user" WHERE id_user = %s', (args.origen,))
        conn.commit()
        print(f'Listo: usuario {args.origen} eliminado, todo quedo en el {args.destino}.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
