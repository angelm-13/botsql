#!/usr/bin/env python3
"""Depura renglones de vale (`nm_incident_product`) duplicados por captura,
copiados tal cual desde adser: el mismo producto aparece mas de una vez
dentro del mismo vale (`id_incident`).

Este NO es el mismo caso que un empleado que vuelve a sacar la misma
herramienta en otra ocasion -- eso es historial real y no se toca. Se
investigo a fondo (ver sesion) y se encontraron 257 grupos producto+vale
repetidos en 44 de los 139 vales; 229 de esos grupos tienen alguna
diferencia real entre sus renglones (mezcla de abierto/cerrado, notas
distintas) que demuestra que son eventos distintos. Solo 28 grupos (42
renglones) son identicos en absolutamente todo (cantidad, direccion,
cerrado/abierto, nota, fechas, ubicaciones, activo de inventario, origen
externo) -- y en varios de ellos el ID de captura prueba que fue el mismo
bloque de renglones guardado dos veces seguidas (IDs consecutivos o con
salto fijo, sin ningun otro vale intercalado). Confirmado con el equipo que
el sistema legado no tiene ninguna funcion de "renovar" o "copiar vale"
automatica, asi que no hay explicacion de negocio para estos 28 grupos mas
alla de una captura duplicada.

Este script SOLO toca un grupo si es identico en todos los campos
comparables -- si un grupo tiene cualquier diferencia real, se dejsa
intacto y se reporta como omitido, nunca se decide a ciegas. Es generico y
recalcula todo en cada corrida: seguro de correr en cualquier ambiente y
de volver a correr despues (no quedan grupos que limpiar).

Se conserva el renglon con el ID mas bajo de cada grupo (el original) y se
marca `deletion_date` en los demas -- igual que el resto de la app, nunca
se hace DELETE fisico.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

CAMPOS_A_COMPARAR = [
    'quantity', 'direction', 'close_date', 'note', 'creation_date', 'last_update_date',
    'start_date', 'due_date', 'id_location_from', 'id_location_to', 'id_inventory_asset',
    'external_id', 'external_source', 'created_by',
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
            "SELECT id_incident, id_product, array_agg(id_nm_incident_product ORDER BY id_nm_incident_product) "
            "FROM nm_incident_product WHERE deletion_date IS NULL "
            "GROUP BY id_incident, id_product HAVING COUNT(*) > 1"
        )
        grupos = cur.fetchall()

        columnas = ', '.join(CAMPOS_A_COMPARAR)
        total_grupos_limpiados = 0
        total_grupos_omitidos = 0
        total_renglones_borrados = 0

        for id_incident, id_product, ids in grupos:
            cur.execute(
                f"SELECT id_nm_incident_product, {columnas} FROM nm_incident_product "
                "WHERE id_nm_incident_product = ANY(%s) ORDER BY id_nm_incident_product",
                (ids,),
            )
            filas = cur.fetchall()
            primero = filas[0][1:]
            son_identicos = all(fila[1:] == primero for fila in filas)

            if not son_identicos:
                total_grupos_omitidos += 1
                print(f"  omitido (hay diferencia real): vale {id_incident}, producto {id_product}, ids {ids}")
                continue

            conservar, *borrar = ids
            if not args.dry_run:
                cur.execute(
                    "UPDATE nm_incident_product SET deletion_date = NOW() WHERE id_nm_incident_product = ANY(%s)",
                    (borrar,),
                )
            total_grupos_limpiados += 1
            total_renglones_borrados += len(borrar)
            print(f"  vale {id_incident}, producto {id_product}: conserva {conservar}, elimina {borrar}")

        if not args.dry_run:
            conn.commit()
            print("\nDepuracion confirmada.")
        else:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")

        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}grupos duplicados encontrados: {len(grupos)}")
        print(f"{prefijo}grupos limpiados (100% identicos): {total_grupos_limpiados}")
        print(f"{prefijo}grupos omitidos (con alguna diferencia real): {total_grupos_omitidos}")
        print(f"{prefijo}renglones {'a marcar' if args.dry_run else 'marcados'} como eliminados: {total_renglones_borrados}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
