#!/usr/bin/env python3
"""Corrige product.path_imagen en adser-prod para que apunte a las fotos
legadas que Tanya conecto via hostPath en /uploads/products.

migrate_adser.py copio path_imagen tal cual desde el dump de MySQL (ej.
"/uploads/producto/2.png", con el nombre de carpeta viejo). La app sirve
imagenes desde /uploads/products (plural) -- sin esta correccion, la URL que
arma el frontend no coincide con ninguna ruta real y la foto sale rota.

No copia ni renombra archivos: los nombres reales (<id_producto>.<ext>) ya
estan en el volumen montado, esto solo alinea la referencia en la base con
lo que ya existe en disco.
"""
from __future__ import annotations

import argparse
import os
import re

import psycopg2

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
FILENAME_RE = re.compile(r'^(\d+)\.([A-Za-z0-9]+)$')


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def archivos_por_id_producto(imagenes_dir: str) -> dict[int, str]:
    resultado = {}
    for nombre in os.listdir(imagenes_dir):
        m = FILENAME_RE.match(nombre)
        if not m:
            continue
        if m.group(2).lower() not in ALLOWED_EXTENSIONS:
            continue
        resultado[int(m.group(1))] = nombre
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imagenes-dir', default='/uploads/products')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    archivos = archivos_por_id_producto(args.imagenes_dir)
    print(f"Archivos con convencion <id>.<ext> en {args.imagenes_dir}: {len(archivos)}")

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_product, path_imagen FROM product")
        filas = cur.fetchall()

        actualizados = 0
        ya_correctos = 0
        sin_archivo = 0

        for id_product, path_actual in filas:
            nombre = archivos.get(id_product)
            if not nombre:
                sin_archivo += 1
                continue
            nuevo_path = f"uploads/products/{nombre}"
            if path_actual == nuevo_path:
                ya_correctos += 1
                continue
            actualizados += 1
            if not args.dry_run:
                cur.execute(
                    "UPDATE product SET path_imagen = %s WHERE id_product = %s",
                    (nuevo_path, id_product),
                )

        if args.dry_run:
            conn.rollback()
            print(f"[dry-run] se actualizarian {actualizados} filas")
        else:
            conn.commit()
            print(f"Actualizadas {actualizados} filas")

        print(f"Ya correctas: {ya_correctos}")
        print(f"Productos sin archivo de imagen encontrado: {sin_archivo}")

        huerfanos = set(archivos) - {fila[0] for fila in filas}
        print(f"Archivos de imagen sin producto correspondiente: {len(huerfanos)}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
