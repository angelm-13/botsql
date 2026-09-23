#!/usr/bin/env python3
"""Depura el catalogo `material` de adser: `migrate_adser.py` paso tal cual
la tabla `material` del legado, que ya traia entradas repetidas para el
mismo tipo de herramienta (misma `material_description` + `id_unit`,
distinto `id_material`) -- un problema de captura preexistente en adser, no
introducido por la migracion (se preservo tal cual, principio acordado con
Alan: "pasar todo tal cual... no queremos mover o afectar nada").

Verificado a mano antes de escribir este script (ver sesion): de 101 grupos
duplicados, 84 no tenian ningun `product` real enganchado (puro ruido de
captura) y 17 si tenian herramientas fisicas repartidas entre 2-3 ids del
mismo grupo -- esas SI se reasignan antes de eliminar el catalogo sobrante,
nunca se tocan los productos en si (su codigo, fecha, color, nota quedan
identicos, solo cambia a que fila de catalogo apuntan).

Este script es generico y recalcula todo en cada corrida (no trae IDs de
adser-prod hardcodeados) -- es seguro correrlo en cualquier ambiente
(tyakxa-dev, adser-prod) y volver a correrlo despues no hace nada (no
quedan grupos duplicados una vez limpiado).

Criterio de canonico: el id con mas `product` reales enganchados gana: en
empate (o si ningun id del grupo tiene productos), gana el id mas bajo --
no cambia nada real, solo decide cual fila de catalogo sobrevive.

Antes de borrar (marcar `deletion_date`) cualquier fila de `material`, se
revisan las 4 tablas que pueden referenciarla (`product`, ademas de
`invoice_material_service`, `material_component` -- como material y como
componente--, y `nm_material_attribute`, vacias hoy en adser-prod/tyakxa-dev
pero se revisan igual por si acaso) y se reasigna cualquier referencia
encontrada al id canonico antes de marcar la fila como eliminada.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

TABLAS_QUE_PUEDEN_REFERENCIAR_MATERIAL = [
    ('invoice_material_service', 'id_material'),
    ('material_component', 'id_material'),
    ('material_component', 'id_component'),
    ('nm_material_attribute', 'id_material'),
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

        cur.execute(
            "SELECT material_description, id_unit, array_agg(id_material ORDER BY id_material) "
            "FROM material WHERE deletion_date IS NULL "
            "GROUP BY material_description, id_unit HAVING COUNT(*) > 1"
        )
        grupos = cur.fetchall()

        total_grupos = 0
        total_productos_reasignados = 0
        total_otras_referencias_reasignadas = 0
        total_filas_borradas = 0

        for descripcion, _id_unit, ids in grupos:
            conteos = {}
            for id_material in ids:
                cur.execute(
                    "SELECT COUNT(*) FROM product WHERE id_material = %s AND deletion_date IS NULL",
                    (id_material,),
                )
                conteos[id_material] = cur.fetchone()[0]

            canonico = sorted(ids, key=lambda i: (-conteos[i], i))[0]
            descartados = [i for i in ids if i != canonico]
            total_grupos += 1
            print(f"  '{descripcion}': conserva id_material={canonico} ({conteos[canonico]} productos), "
                  f"descarta {descartados}")

            for id_material in descartados:
                n_productos = conteos[id_material]
                if n_productos:
                    if not args.dry_run:
                        cur.execute(
                            "UPDATE product SET id_material = %s WHERE id_material = %s",
                            (canonico, id_material),
                        )
                    total_productos_reasignados += n_productos
                    print(f"    -> {n_productos} producto(s) reasignados de id_material={id_material} a {canonico}")

                for tabla, columna in TABLAS_QUE_PUEDEN_REFERENCIAR_MATERIAL:
                    cur.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {columna} = %s", (id_material,))
                    (m,) = cur.fetchone()
                    if m:
                        if not args.dry_run:
                            cur.execute(f"UPDATE {tabla} SET {columna} = %s WHERE {columna} = %s", (canonico, id_material))
                        total_otras_referencias_reasignadas += m
                        print(f"    -> aviso: {tabla}.{columna} tambien referenciaba id_material={id_material} "
                              f"({m} fila(s)), reasignado a {canonico}")

                if not args.dry_run:
                    cur.execute("UPDATE material SET deletion_date = NOW() WHERE id_material = %s", (id_material,))
                total_filas_borradas += 1

        if not args.dry_run:
            conn.commit()
            print("\nDepuracion confirmada.")
        else:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")

        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}grupos duplicados encontrados: {total_grupos}")
        print(f"{prefijo}productos reasignados: {total_productos_reasignados}")
        print(f"{prefijo}otras referencias reasignadas (deberia ser 0 hoy): {total_otras_referencias_reasignadas}")
        print(f"{prefijo}filas de material {'a marcar' if args.dry_run else 'marcadas'} como eliminadas: {total_filas_borradas}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
