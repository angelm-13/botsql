#!/usr/bin/env python3
"""Pasa la descripcion de los productos YA existentes a formato de oracion.

El sistema anterior guardo casi todo en MAYUSCULAS ("PULIDOR CHICO 3/4"); el
formulario de producto ahora pide "Pulidor chico 3/4" (ver
app/utils/product_description.py, que es la UNICA definicion de la regla). Este
script pone los productos migrados al mismo formato.

Por omision solo toca las descripciones escritas TODAS en mayusculas, que es
el caso del legado y donde la conversion es segura. Un texto mixto
("Desarmador plano Truper") puede llevar una marca o un nombre propio con su
mayuscula: se deja y solo se cuenta; con --incluir-mixtos tambien se normaliza.

Las siglas conocidas (PVC, LED...) se conservan; una sigla que no este en la
lista se baja a minusculas en un texto todo en mayusculas, asi que conviene
mirar el --dry-run antes de aplicar. --respaldo guarda un CSV con el antes y el
despues para poder revertir.

Idempotente: una descripcion ya valida no se toca.

--restaurar <csv> deshace una corrida con el CSV de --respaldo: devuelve el
"antes" solo en las filas que siguen diciendo el "despues" (si alguien ya la
edito a mano, no se pisa).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.utils.product_description import es_valida, sugerir  # noqa: E402


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def esta_en_mayusculas(texto: str) -> bool:
    return not any(c.islower() for c in texto)


def restaurar(ruta: str, dry_run: bool):
    with open(ruta, newline='', encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    conn = conectar()
    try:
        cur = conn.cursor()
        devueltas = 0
        for fila in filas:
            cur.execute(
                "UPDATE product SET descripcion = %s "
                "WHERE id_product = %s AND descripcion = %s",
                (fila['antes'], int(fila['id_product']), fila['despues']))
            devueltas += cur.rowcount
        print(f"Filas del respaldo: {len(filas)}; restauradas: {devueltas}")
        if dry_run:
            conn.rollback()
            print("[dry-run] no se escribio nada")
        else:
            conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--incluir-mixtos', action='store_true')
    parser.add_argument('--respaldo', help='CSV con id_product, antes, despues')
    parser.add_argument('--muestra', type=int, default=15)
    parser.add_argument('--restaurar', help='CSV de --respaldo cuyo "antes" se devuelve')
    args = parser.parse_args()

    if args.restaurar:
        return restaurar(args.restaurar, args.dry_run)

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_product, descripcion FROM product "
                    "WHERE deletion_date IS NULL AND descripcion IS NOT NULL "
                    "AND btrim(descripcion) <> '' ORDER BY id_product")
        filas = cur.fetchall()

        cambios = []
        ya_validas = 0
        mixtos_omitidos = 0
        for id_product, texto in filas:
            if es_valida(texto):
                ya_validas += 1
                continue
            nuevo = sugerir(texto)
            if not esta_en_mayusculas(texto) and not args.incluir_mixtos:
                mixtos_omitidos += 1
                continue
            if nuevo and nuevo != texto and len(nuevo) <= 250:
                cambios.append((id_product, texto, nuevo))

        print(f"Productos con descripcion: {len(filas)}")
        print(f"Ya en formato de oracion: {ya_validas}")
        print(f"Mixtos sin tocar (usa --incluir-mixtos): {mixtos_omitidos}")
        print(f"A normalizar: {len(cambios)}")
        for id_product, antes, despues in cambios[:args.muestra]:
            print(f"  #{id_product}: {antes!r} -> {despues!r}")

        if args.respaldo and cambios:
            with open(args.respaldo, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['id_product', 'antes', 'despues'])
                w.writerows(cambios)
            print(f"Respaldo escrito en {args.respaldo}")

        if args.dry_run:
            conn.rollback()
            print("[dry-run] no se escribio nada")
            return
        for id_product, _antes, despues in cambios:
            cur.execute("UPDATE product SET descripcion = %s WHERE id_product = %s",
                        (despues, id_product))
        conn.commit()
        print(f"Actualizadas {len(cambios)} filas")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
