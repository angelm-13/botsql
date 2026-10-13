#!/usr/bin/env python3
"""Alinea la marca y la familia del MATERIAL con las que el catalogo capturo
en el PRODUCTO, para que la traza de inventario deje de avisar "El catalogo
publico lo clasifica distinto".

Por que hay discrepancias
-------------------------
`material.id_brand` / `material.id_product_family` son NOT NULL: lo migrado sin
dato quedo en los centinelas "Sin marca especifica" / "Sin categoria".
`product.id_marca` / `product.id_familia` son otra captura (sin llave ajena) que
si traia el dato. La traza lee del material, asi que muestra el centinela y avisa
que el catalogo dice otra cosa.

Que hace (y que no)
-------------------
1. Material en centinela + sus productos coinciden en UN solo valor valido
   -> se copia ese valor al material. Es el unico cambio por omision.
2. Material en centinela + sus productos discrepan entre si -> NO se toca,
   se lista para revision manual.
3. Material con marca/familia REAL distinta de la del producto -> NO se toca,
   se lista (hay que decidir cual de las dos es la correcta).
4. Id del producto que ya no existe en `brand`/`product_family` (huerfano) -> NO
   se toca, se lista. Solo con `--limpiar-huerfanos` se pone NULL en el
   producto. Ojo: el KPI por familia agrupa por `product.id_familia`, asi que
   ese flag mueve esos productos a "Sin familia" en el tablero.

Nunca escribe `product.cantidad` ni toca el libro de movimientos.

Respaldo: antes de escribir, guarda en un CSV los valores anteriores de cada
fila que va a cambiar (`--respaldo`). Con `--dry-run` no escribe nada.
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime

import psycopg2

SIN_MARCA = 'Sin marca específica'
SIN_FAMILIA = 'Sin categoría'


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def id_centinela(cur, tabla, pk, columna, descripcion):
    cur.execute(f"SELECT {pk} FROM {tabla} WHERE {columna} = %s", (descripcion,))
    ids = [r[0] for r in cur.fetchall()]
    if len(ids) != 1:
        raise SystemExit(
            f"Se esperaba exactamente un '{descripcion}' en {tabla} y hay {len(ids)}; "
            "no se adivina cual es el centinela.")
    return ids[0]


def existentes(cur, tabla, pk):
    cur.execute(f"SELECT {pk} FROM {tabla}")
    return {r[0] for r in cur.fetchall()}


def planear(cur, eje):
    """Devuelve (cambios, ambiguos, distintos_reales, huerfanos) para un eje.

    eje = 'marca' o 'familia'.
    """
    if eje == 'marca':
        col_p, col_m = 'id_marca', 'id_brand'
        tabla, pk = 'brand', 'id_brand'
        centinela = id_centinela(cur, 'brand', 'id_brand', 'brand_description', SIN_MARCA)
    else:
        col_p, col_m = 'id_familia', 'id_product_family'
        tabla, pk = 'product_family', 'id_product_family'
        centinela = id_centinela(cur, 'product_family', 'id_product_family',
                                 'product_family_description', SIN_FAMILIA)
    validos = existentes(cur, tabla, pk)

    cur.execute(
        f"SELECT p.id_product, p.product_code, p.{col_p}, m.id_material, m.{col_m} "
        f"FROM product p JOIN material m ON m.id_material = p.id_material "
        f"WHERE p.{col_p} IS NOT NULL")
    por_material = defaultdict(set)   # id_material -> {valores validos de sus productos}
    actual = {}                       # id_material -> valor actual en el material
    distintos_reales, huerfanos = [], []
    for id_product, code, val_p, id_material, val_m in cur.fetchall():
        actual[id_material] = val_m
        if val_p not in validos:
            huerfanos.append((id_product, code, val_p))
            continue
        if val_p == val_m:
            continue
        if val_m == centinela:
            por_material[id_material].add(val_p)
        else:
            distintos_reales.append((id_product, code, val_m, val_p))

    cambios, ambiguos = [], []
    for id_material, valores in por_material.items():
        valores.discard(centinela)
        if len(valores) == 1:
            cambios.append((id_material, actual[id_material], next(iter(valores))))
        elif len(valores) > 1:
            ambiguos.append((id_material, sorted(valores)))
    return col_m, cambios, ambiguos, distintos_reales, huerfanos


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limpiar-huerfanos', action='store_true',
                    help='pone NULL en product.id_marca/id_familia que apuntan a algo inexistente')
    ap.add_argument('--respaldo', default=None,
                    help='ruta del CSV de respaldo (por omision, uno con fecha en el cwd)')
    args = ap.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        respaldo = []   # (tabla, id, columna, valor_anterior)
        for eje in ('marca', 'familia'):
            col_m, cambios, ambiguos, reales, huerf = planear(cur, eje)
            print(f"\n== {eje.upper()} ==")
            print(f"Materiales a corregir (centinela -> valor del catalogo): {len(cambios)}")
            print(f"Materiales ambiguos (sus productos discrepan entre si, no se tocan): {len(ambiguos)}")
            for id_material, valores in ambiguos[:20]:
                print(f"   material {id_material}: productos dicen {valores}")
            print(f"Productos con {eje} real distinta de la del material (revision manual): {len(reales)}")
            for fila in reales[:20]:
                print(f"   producto {fila[0]} ({fila[1]}): material={fila[2]} catalogo={fila[3]}")
            print(f"Productos con id de {eje} inexistente: {len(huerf)}")
            for fila in huerf[:20]:
                print(f"   producto {fila[0]} ({fila[1]}): id {fila[2]} ya no existe")

            for id_material, viejo, nuevo in cambios:
                respaldo.append(('material', id_material, col_m, viejo))
                if not args.dry_run:
                    cur.execute(
                        f"UPDATE material SET {col_m} = %s, last_update_date = now() "
                        f"WHERE id_material = %s", (nuevo, id_material))
            if args.limpiar_huerfanos:
                col_p = 'id_marca' if eje == 'marca' else 'id_familia'
                for id_product, _code, viejo in huerf:
                    respaldo.append(('product', id_product, col_p, viejo))
                    if not args.dry_run:
                        cur.execute(f"UPDATE product SET {col_p} = NULL WHERE id_product = %s",
                                    (id_product,))

        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] no se escribio nada ({len(respaldo)} cambios se harian).")
            return
        ruta = args.respaldo or f"respaldo_marca_familia_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(ruta, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['tabla', 'id', 'columna', 'valor_anterior'])
            w.writerows(respaldo)
        conn.commit()
        print(f"\nCommit hecho: {len(respaldo)} cambios. Respaldo con los valores anteriores: {ruta}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
