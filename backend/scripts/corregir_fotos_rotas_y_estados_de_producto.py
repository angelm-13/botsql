#!/usr/bin/env python3
"""Corrige dos datos de producto que quedaron mal: fotos rotas y estados contradictorios.

Por que existe
--------------
1. **Fotos rotas.** 46 productos de adser-prod (ej. ACE133) traen
   `path_imagen = '/uploads/producto/<CODIGO>.png'`, una ruta del sistema anterior
   cuyo archivo nunca llego (la carpeta guarda `<id>.<ext>` y las subidas nuevas
   `p_<id>.<ext>`). La pantalla pinta un icono roto y, como la ruta no esta vacia,
   tampoco hereda la foto de su material.
2. **Estado doble.** `product_status` (texto) e `id_inventory_status` (catalogo) se
   guardaban por separado: MARR4 decia "usado" con el catalogo en "extraviado".
   Desde ahora `ProductService` los escribe juntos; esto arregla lo ya guardado.

Que toca (y que NO)
-------------------
Fotos: productos vivos con `path_imagen` cuyo archivo NO esta en `--imagenes-dir`.
  - si existe `p_<id>.<ext>` o `<id>.<ext>`, la ruta apunta a ese archivo;
  - si no, queda NULL (el producto hereda la foto de su material, o pide una nueva).
  Un `path_imagen` cuyo archivo existe no se toca.
Estados: productos vivos cuyo texto dice un estado de catalogo (ver
`app/utils/product_status.py`) y cuyo `id_inventory_status` es otro o esta vacio. El
texto manda -es lo que alguien escogio en el formulario-; el catalogo se alinea.
El texto no se reescribe, no se toca ENTRADA/SALIDA ni un producto sin texto.

Uso (dentro del backend del ambiente):
    python scripts/corregir_fotos_rotas_y_estados_de_producto.py --dry-run
    python scripts/corregir_fotos_rotas_y_estados_de_producto.py --respaldo /uploads/respaldo_AAAA-MM-DD.csv

`--dry-run` revierte todo y no escribe el respaldo. Sin `--dry-run` el respaldo (id,
columna, valor anterior, valor nuevo) se escribe ANTES de confirmar; si no se puede
escribir, no se cambia nada. Idempotente: una segunda corrida ya no encuentra nada.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg2  # noqa: E402

from app.utils.product_status import codigo_de_catalogo  # noqa: E402

PREFIJO_DE_RUTA = re.compile(r'^/?uploads/(?:producto|products)/')


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def archivos_por_producto(carpeta: Path) -> tuple[set[str], dict[int, str]]:
    """Los nombres que hay en disco y, por id de producto, el archivo que le toca."""
    nombres = {p.name for p in carpeta.iterdir() if p.is_file()}
    por_id: dict[int, str] = {}
    for nombre in sorted(nombres):
        coincide = re.match(r'^(?:p_)?(\d+)\.[A-Za-z0-9]+$', nombre)
        if not coincide:
            continue
        id_producto = int(coincide.group(1))
        # `p_<id>` (subida nueva) gana sobre `<id>` (migrada): es la mas reciente.
        if id_producto not in por_id or nombre.startswith('p_'):
            por_id[id_producto] = nombre
    return nombres, por_id


def fotos_rotas(cur, carpeta: Path):
    nombres, por_id = archivos_por_producto(carpeta)
    cur.execute(
        "SELECT id_product, product_code, path_imagen FROM product "
        "WHERE deletion_date IS NULL AND coalesce(btrim(path_imagen), '') <> '' "
        "ORDER BY id_product")
    cambios = []
    for id_producto, codigo, ruta in cur.fetchall():
        if PREFIJO_DE_RUTA.sub('', ruta) in nombres:
            continue
        nuevo_nombre = por_id.get(id_producto)
        nueva = f'uploads/products/{nuevo_nombre}' if nuevo_nombre else None
        cambios.append((id_producto, codigo, ruta, nueva))
    return cambios


def estados_contradictorios(cur):
    cur.execute(
        "SELECT p.id_product, p.product_code, p.product_status, p.id_inventory_status, "
        "       s.inventory_status_code "
        "FROM product p LEFT JOIN inventory_status s ON s.id_inventory_status = p.id_inventory_status "
        "WHERE p.deletion_date IS NULL AND coalesce(btrim(p.product_status), '') <> '' "
        "ORDER BY p.id_product")
    filas = cur.fetchall()
    cur.execute(
        "SELECT inventory_status_code, id_inventory_status FROM inventory_status "
        "WHERE entity_scope = 'product' AND deletion_date IS NULL")
    id_de = dict(cur.fetchall())
    cambios = []
    for id_producto, codigo, texto, id_actual, codigo_actual in filas:
        quiere = codigo_de_catalogo(texto)
        if quiere is None or quiere == codigo_actual or quiere not in id_de:
            continue
        cambios.append((id_producto, codigo, texto, id_actual, codigo_actual, id_de[quiere], quiere))
    return cambios


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--imagenes-dir', default='/uploads/products',
                        help='carpeta donde estan las fotos de producto (default /uploads/products)')
    parser.add_argument('--respaldo', default=None,
                        help='ruta del CSV con los valores anteriores (por omision, uno con fecha en /tmp)')
    args = parser.parse_args()

    carpeta = Path(args.imagenes_dir)
    if not carpeta.is_dir():
        raise SystemExit(f"--imagenes-dir no existe: {carpeta}")
    ruta = args.respaldo or f"/tmp/respaldo_producto_{datetime.now():%Y%m%d_%H%M%S}.csv"

    conn = conectar()
    try:
        cur = conn.cursor()
        fotos = fotos_rotas(cur, carpeta)
        estados = estados_contradictorios(cur)

        print(f"fotos con ruta rota: {len(fotos)} "
              f"({sum(1 for f in fotos if f[3])} se reapuntan, {sum(1 for f in fotos if not f[3])} quedan vacias)")
        for id_producto, codigo, vieja, nueva in fotos:
            print(f"  #{id_producto}  {codigo or ''}  {vieja}  ->  {nueva or 'NULL'}")

        print(f"\nestados contradictorios: {len(estados)}")
        resumen = Counter((t, ca, q) for _, _, t, _, ca, _, q in estados)
        for (texto, actual, quiere), cuantos in sorted(resumen.items(), key=lambda x: -x[1]):
            print(f"  {cuantos:>4}  texto={texto!r:14} catalogo {actual or 'vacio'} -> {quiere}")
        for id_producto, codigo, texto, _, actual, _, quiere in estados[:30]:
            print(f"  #{id_producto}  {codigo or ''}  {texto!r}: {actual or 'vacio'} -> {quiere}")

        if not fotos and not estados:
            print("\nnada que corregir.")
            return

        if not args.dry_run:
            with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(['id_product', 'product_code', 'columna', 'valor_anterior', 'valor_nuevo'])
                for id_producto, codigo, vieja, nueva in fotos:
                    escritor.writerow([id_producto, codigo, 'path_imagen', vieja, nueva])
                for id_producto, codigo, _, id_actual, _, id_nuevo, _ in estados:
                    escritor.writerow([id_producto, codigo, 'id_inventory_status', id_actual, id_nuevo])
            print(f"\nrespaldo escrito en {ruta}")

        for id_producto, _, _, nueva in fotos:
            cur.execute("UPDATE product SET path_imagen = %s, last_update_date = now() WHERE id_product = %s",
                        (nueva, id_producto))
        for id_producto, _, _, _, _, id_nuevo, _ in estados:
            cur.execute("UPDATE product SET id_inventory_status = %s, last_update_date = now() WHERE id_product = %s",
                        (id_nuevo, id_producto))

        if args.dry_run:
            conn.rollback()
            print(f"\n--dry-run: {len(fotos)} fotos y {len(estados)} estados se corregirian; "
                  "todo revertido, no se escribio nada.")
        else:
            conn.commit()
            print(f"\nCorreccion confirmada: {len(fotos)} fotos y {len(estados)} estados.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
