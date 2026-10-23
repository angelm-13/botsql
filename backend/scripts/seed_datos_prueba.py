"""Carga datos de prueba sinteticos en TODAS las tablas de negocio.

Lee el esquema vivo (information_schema + pg_constraint), ordena las tablas por
llaves foraneas y genera filas verosimiles segun el nombre y el tipo de cada
columna. Esta pensado para ambientes de desarrollo/prueba -- p. ej. probar el
modulo BI --; NO usar contra datos reales.

    docker compose exec backend python scripts/seed_datos_prueba.py --yes
    ... --filas 15 --semilla 7 --solo invoice,product

Si una fila viola algun CHECK/UNIQUE se reintenta con otros valores y, si no
hay forma, se omite (el resumen final lista las tablas que quedaron vacias).
No toca las tablas de catalogo/seguridad (permisos, campos, KPIs, secretos).
"""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import json
import os
import random
import re
import sys
import uuid
from collections import defaultdict

import psycopg2
import psycopg2.extras

SALTAR = {
    "entity_permission", "field", "nm_field_permission", "permission",
    "bi_department_permission", "kpi_definition", "user_mfa",
    "password_reset_token", "public_api_key", "pac_config", "event_log",
    "document_category", "schema_migration", "alembic_version",
}
# Tablas que merecen mas volumen: son las que se preguntan en un dashboard.
GRANDES = {
    "invoice": 60, "invoice_payment": 40, "product": 80, "material": 40,
    "incident": 50, "nm_incident_product": 80, "pos_sale": 60, "pos_sale_item": 150,
    "customer_supplier": 25, "ticket": 40, "task": 40, "inventory_stock": 60,
    "restaurant_order": 50, "restaurant_order_item": 120, "payroll_detail": 30,
    "movement": 50, "logistics_trip": 30, "user": 20,
}

NOMBRES = ["Ana", "Luis", "Carlos", "María", "José", "Laura", "Pedro", "Sofía", "Miguel",
           "Elena", "Jorge", "Paola", "Diego", "Lucía", "Andrés", "Valeria"]
APELLIDOS = ["García", "Hernández", "López", "Martínez", "González", "Pérez", "Rodríguez",
             "Sánchez", "Ramírez", "Torres", "Flores", "Díaz", "Cruz", "Morales"]
EMPRESAS = ["Aceros del Norte", "Vidrios Monterrey", "Comercial Aurora", "Grupo Zafiro",
            "Distribuidora Atlas", "Servicios Delta", "Construcciones Omega", "Aluminios Sol",
            "Tecnologías Nova", "Alimentos La Cosecha", "Transportes Rápidos", "Ferretería Central"]
PRODUCTOS = ["Ventana corrediza", "Puerta de aluminio", "Vidrio templado 6mm", "Perfil 3 pulgadas",
             "Herraje bisagra", "Cancel de baño", "Espejo biselado", "Mosquitero", "Sellador silicón",
             "Riel superior", "Jaladera acero", "Cristal laminado", "Tornillo inox", "Burlete"]
CIUDADES = ["Monterrey", "Guadalajara", "Ciudad de México", "Puebla", "Querétaro", "León", "Mérida"]
ESTADOS = ["activo", "pendiente", "completado", "cancelado", "en proceso"]


class Col:
    def __init__(self, r):
        (self.nombre, self.tipo, self.udt, self.nulo, self.defecto, self.largo,
         self.prec, self.escala, self.identidad, self.generada) = r

    @property
    def tiene_defecto(self):
        return self.defecto is not None or self.identidad == "YES" or self.generada == "ALWAYS"


def conectar():
    url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI", "")
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


def leer_esquema(cur):
    cur.execute("""select table_name from information_schema.tables
                   where table_schema='public' and table_type='BASE TABLE' order by 1""")
    tablas = [r[0] for r in cur.fetchall()]
    cur.execute("""select table_name, column_name, data_type, udt_name,
                          is_nullable='YES', column_default, character_maximum_length,
                          numeric_precision, numeric_scale, is_identity, is_generated
                   from information_schema.columns where table_schema='public'
                   order by table_name, ordinal_position""")
    columnas = defaultdict(list)
    for r in cur.fetchall():
        columnas[r[0]].append(Col(r[1:]))
    cur.execute("""select c.conrelid::regclass::text, c.conname, c.contype,
                          pg_get_constraintdef(c.oid),
                          array(select a.attname from pg_attribute a
                                where a.attrelid=c.conrelid and a.attnum = any(c.conkey)),
                          c.confrelid::regclass::text,
                          array(select a.attname from pg_attribute a
                                where a.attrelid=c.confrelid and a.attnum = any(c.confkey))
                   from pg_constraint c join pg_namespace n on n.oid=c.connamespace
                   where n.nspname='public'""")
    pks, fks, uniques, checks = {}, defaultdict(list), defaultdict(set), defaultdict(list)
    for tabla, _n, tipo, defn, cols, ftabla, fcols in cur.fetchall():
        tabla = tabla.replace('"', "")
        if tipo == "p":
            pks[tabla] = cols
            if len(cols) == 1:
                uniques[tabla].add(cols[0])
        elif tipo == "u" and len(cols) == 1:
            uniques[tabla].add(cols[0])
        elif tipo == "f" and len(cols) == 1:
            fks[tabla].append((cols[0], ftabla.replace('"', ""), fcols[0]))
        elif tipo == "c":
            checks[tabla].append(defn)
    cur.execute("""select t.relname, a.attname from pg_index i
                   join pg_class t on t.oid=i.indrelid join pg_namespace n on n.oid=t.relnamespace
                   join pg_attribute a on a.attrelid=t.oid and a.attnum = any(i.indkey)
                   where i.indisunique and n.nspname='public' and i.indnatts=1""")
    for t, c in cur.fetchall():
        uniques[t].add(c)
    return tablas, columnas, pks, fks, uniques, checks


def orden_topologico(tablas, columnas, fks):
    nulos = {t: {c.nombre: c.nulo for c in columnas[t]} for t in tablas}
    deps = {t: set() for t in tablas}
    for t in tablas:
        for col, ftabla, _ in fks[t]:
            if ftabla != t and ftabla in deps and not nulos[t].get(col, True):
                deps[t].add(ftabla)
    hechas, orden = set(), []
    pendientes = set(tablas)
    while pendientes:
        listas = sorted(t for t in pendientes if deps[t] <= hechas)
        if not listas:                       # ciclo: se sueltan las FK nulas
            listas = [sorted(pendientes)[0]]
        for t in listas:
            orden.append(t)
            hechas.add(t)
            pendientes.discard(t)
    # las FK anulables se resuelven despues si el padre aun no tenia filas
    return orden


def valores_de_check(defn: str, col: str):
    """Extrae los literales permitidos de un CHECK tipo IN/ANY(ARRAY[...])."""
    if col not in defn:
        return None
    if not re.search(r"ANY|IN \(|= '", defn):
        return None
    lit = re.findall(r"'((?:[^']|'')*)'::", defn) or re.findall(r"'((?:[^']|'')*)'", defn)
    return [x.replace("''", "'") for x in lit] or None


class Generador:
    def __init__(self, cur, rng, args):
        self.cur, self.rng, self.args = cur, rng, args
        (self.tablas, self.columnas, self.pks, self.fks,
         self.uniques, self.checks) = leer_esquema(cur)
        self.ids: dict[tuple[str, str], list] = {}
        self.contador = defaultdict(int)
        self.hoy = dt.date.today()

    # -- padres ---------------------------------------------------------
    def valores_padre(self, tabla, col):
        k = (tabla, col)
        if k not in self.ids:
            self.cur.execute(f'select "{col}" from public."{tabla}" limit 500')
            self.ids[k] = [r[0] for r in self.cur.fetchall()]
        return self.ids[k]

    # -- valores por tipo -----------------------------------------------
    def texto(self, tabla, col: Col, n):
        c, r = col.nombre.lower(), self.rng
        largo = col.largo or 200
        if "email" in c or "correo" in c:
            v = f"usuario{n}@ejemplo.com"
        elif "phone" in c or "tel" in c or "celular" in c:
            v = "".join(r.choice("0123456789") for _ in range(10))
        elif c == "rfc" or c.endswith("_rfc") or c.startswith("rfc"):
            v = "XAXX010101000" if r.random() < .3 else f"EKU{r.randint(100000, 999999)}AB{r.randint(1, 9)}"
        elif "postal" in c or c in ("zip", "cp"):
            v = f"{r.randint(10000, 99999)}"
        elif "city" in c or "ciudad" in c or "municip" in c:
            v = r.choice(CIUDADES)
        elif "state" in c and "status" not in c:
            v = r.choice(["Nuevo León", "Jalisco", "CDMX", "Puebla"])
        elif "country" in c or "pais" in c:
            v = "México"
        elif "address" in c or "street" in c or "calle" in c or "direccion" in c:
            v = f"Calle {r.choice(APELLIDOS)} {r.randint(1, 999)}, Col. Centro"
        elif "username" in c or c == "user_name" or c == "login":
            v = f"usuario{n}"
        elif "password" in c or "hash" in c or "secret" in c or "token" in c:
            v = "x" * 20
        elif "uuid" in c or "folio_fiscal" in c:
            v = str(uuid.UUID(int=r.getrandbits(128)))
        elif "url" in c or "path" in c or "image" in c or "file" in c:
            v = f"uploads/demo/{tabla}_{n}.png"
        elif "currency" in c or "moneda" in c:
            v = r.choice(["MXN", "MXN", "MXN", "USD"])
        elif "color" in c:
            v = r.choice(["#1b7a60", "#173b66", "#b91c1c"])
        elif "status" in c or "estatus" in c or "estado" in c or "state" in c:
            v = r.choice(ESTADOS)
        elif "first_name" in c or c in ("nombre", "name") and tabla in ("user", "logistics_operator", "restaurant_waiter", "customer_contact"):
            v = r.choice(NOMBRES)
        elif "last_name" in c or "apellido" in c:
            v = r.choice(APELLIDOS)
        elif "customer" in tabla and ("name" in c or "razon" in c):
            v = f"{r.choice(EMPRESAS)} {n}"
        elif tabla in ("product", "material", "pos_product_variant", "restaurant_dish") and ("desc" in c or "name" in c):
            v = f"{r.choice(PRODUCTOS)} {n}"
        elif "code" in c or "codigo" in c or "folio" in c or "number" in c or "serie" in c or c in ("sku", "plate", "placas"):
            v = f"{tabla[:4].upper()}-{n:05d}"
        elif "name" in c or "nombre" in c:
            v = f"{r.choice(NOMBRES)} {r.choice(APELLIDOS)}"
        elif "desc" in c or "title" in c or "concept" in c or "note" in c or "comment" in c or "observ" in c:
            v = f"{tabla.replace('_', ' ').capitalize()} de prueba {n}"
        else:
            v = f"{c[:12]}-{n}"
        if col.nombre in self.uniques[tabla] and not v.endswith(str(n)):
            v = f"{v}-{n}"
        return v[:largo]

    def numero(self, tabla, col: Col):
        c, r = col.nombre.lower(), self.rng
        escala = col.escala or 0
        if any(k in c for k in ("rate", "tax", "iva", "percent", "porcent", "discount", "descuento")):
            v = r.choice([0, 8, 16]) if escala else r.randint(0, 16)
        elif any(k in c for k in ("amount", "total", "price", "precio", "cost", "costo", "subtotal",
                                  "balance", "saldo", "salary", "salario", "importe", "monto", "paid")):
            v = round(r.uniform(150, 45000), 2)
        elif any(k in c for k in ("qty", "quantity", "cantidad", "stock", "existencia", "units")):
            v = r.randint(1, 150)
        elif any(k in c for k in ("year", "anio")):
            v = self.hoy.year
        elif c.startswith("month") or c.endswith("month"):
            v = r.randint(1, 12)
        elif any(k in c for k in ("lat",)):
            v = round(r.uniform(19.0, 26.0), 6)
        elif any(k in c for k in ("lon", "lng")):
            v = round(r.uniform(-103.5, -98.0), 6)
        else:
            v = round(r.uniform(1, 500), 2) if escala else r.randint(1, 500)
        if col.prec:
            tope = 10 ** (col.prec - escala) - 1
            v = min(v, tope)
        return decimal.Decimal(str(v)) if escala else int(v)

    def fecha(self, col: Col):
        c, r = col.nombre.lower(), self.rng
        if any(k in c for k in ("expir", "due", "vence", "end", "fin", "deadline", "close")):
            return self.hoy + dt.timedelta(days=r.randint(1, 90))
        if "born" in c or "birth" in c or "nacimiento" in c:
            return self.hoy - dt.timedelta(days=r.randint(365 * 20, 365 * 55))
        return self.hoy - dt.timedelta(days=r.randint(0, 365))

    def valor(self, tabla, col: Col, n):
        t = col.udt
        if t in ("int2", "int4", "int8", "numeric", "float4", "float8"):
            return self.numero(tabla, col)
        if t == "bool":
            return self.rng.random() < .6
        if t == "date":
            return self.fecha(col)
        if t in ("timestamp", "timestamptz"):
            d = self.fecha(col)
            return dt.datetime(d.year, d.month, d.day, self.rng.randint(7, 20), self.rng.randint(0, 59))
        if t in ("time", "timetz"):
            return dt.time(self.rng.randint(7, 20), self.rng.choice([0, 15, 30, 45]))
        if t in ("json", "jsonb"):
            return psycopg2.extras.Json({})
        if t == "uuid":
            return str(uuid.UUID(int=self.rng.getrandbits(128)))
        if t == "bytea":
            return b""
        if t in ("varchar", "text", "bpchar", "citext"):
            return self.texto(tabla, col, n)
        return None

    # -- una fila -------------------------------------------------------
    def fila(self, tabla, n, intento):
        valores = {}
        fk_de = {c: (ft, fc) for c, ft, fc in self.fks[tabla]}
        for col in self.columnas[tabla]:
            if col.generada == "ALWAYS" or col.identidad == "YES" and False:
                continue
            nom = col.nombre
            es_pk_serial = nom in self.pks.get(tabla, []) and col.tiene_defecto
            if es_pk_serial:
                continue
            if nom in fk_de:
                ft, fc = fk_de[nom]
                ops = self.valores_padre(ft, fc)
                if ops:
                    valores[nom] = self.rng.choice(ops)
                elif col.nulo:
                    valores[nom] = None
                else:
                    self.motivo = f"padre vacio: {ft}"
                    return None
                continue
            permitidos = None
            for ck in self.checks[tabla]:
                permitidos = valores_de_check(ck, nom) or permitidos
            if permitidos and col.udt in ("varchar", "text", "bpchar"):
                valores[nom] = self.rng.choice(permitidos)
                continue
            if col.tiene_defecto and (col.nulo or intento == 0) and nom.lower() not in (
                    "creation_date", "created_at") and not re.search(r"date|fecha|time", nom.lower()):
                if self.rng.random() < .8:
                    continue                       # que el defecto de la base decida
            if col.nulo and self.rng.random() < (.05 if intento == 0 else .5):
                valores[nom] = None
                continue
            if nom in self.pks.get(tabla, []):
                self.cur.execute(f'select coalesce(max("{nom}"),0)+1 from public."{tabla}"')
                valores[nom] = self.cur.fetchone()[0]
                continue
            v = self.valor(tabla, col, n)
            if v is None and not col.nulo:
                self.motivo = f"sin generador para {nom} ({col.udt})"
                return None
            valores[nom] = v
        # consistencia basica de importes
        if "subtotal" in valores and "total" in valores and valores["subtotal"] is not None \
                and isinstance(valores["subtotal"], (int, float, decimal.Decimal)):
            valores["total"] = (decimal.Decimal(str(valores["subtotal"])) * decimal.Decimal("1.16")).quantize(decimal.Decimal("0.01"))
        return valores

    def poblar(self, tabla, objetivo):
        cur = self.cur
        cur.execute(f'select count(*) from public."{tabla}"')
        existentes = cur.fetchone()[0]
        ok, errores = 0, defaultdict(int)
        for n in range(existentes + 1, max(objetivo, existentes) + 1):
            insertada = False
            for intento in range(6):
                datos = self.fila(tabla, n + intento * 1000, intento)
                if not datos:
                    errores[getattr(self, "motivo", "sin valor")] += 1
                    break
                cols = ", ".join(f'"{c}"' for c in datos)
                marc = ", ".join(["%s"] * len(datos))
                cur.execute("savepoint s")
                try:
                    cur.execute(f'insert into public."{tabla}" ({cols}) values ({marc})', list(datos.values()))
                    cur.execute("release savepoint s")
                    insertada = True
                    ok += 1
                    break
                except psycopg2.Error as e:
                    cur.execute("rollback to savepoint s")
                    errores[str(e).splitlines()[0][:110]] += 1
            if not insertada and not errores:
                errores["sin intento"] += 1
        # los ids nuevos deben verse como padres para las siguientes tablas
        for k in [k for k in self.ids if k[0] == tabla]:
            del self.ids[k]
        return ok, errores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--filas", type=int, default=12, help="filas por tabla (las grandes usan mas)")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--solo", default="", help="tablas separadas por coma")
    ap.add_argument("--yes", action="store_true", help="confirma que es una base de pruebas")
    args = ap.parse_args()
    if not args.yes:
        sys.exit("Esto inserta datos sinteticos en TODAS las tablas. Repite con --yes en una base de pruebas.")

    con = conectar()
    cur = con.cursor()
    g = Generador(cur, random.Random(args.semilla), args)
    solo = {t.strip() for t in args.solo.split(",") if t.strip()}
    orden = [t for t in orden_topologico(g.tablas, g.columnas, g.fks)
             if t not in SALTAR and (not solo or t in solo)]
    vacias, resumen = [], []
    for tabla in orden:
        objetivo = GRANDES.get(tabla, args.filas)
        ok, errores = g.poblar(tabla, objetivo)
        resumen.append((tabla, ok))
        if ok == 0:
            vacias.append((tabla, dict(list(errores.items())[:2])))
        print(f"{tabla:42s} +{ok}", flush=True)
    con.commit()
    print(f"\nListo: {sum(o for _, o in resumen)} filas en {sum(1 for _, o in resumen if o)} tablas.")
    if vacias:
        print("\nTablas sin filas nuevas:")
        for t, e in vacias:
            print(f"  {t}: {e}")


if __name__ == "__main__":
    main()
