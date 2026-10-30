#!/usr/bin/env python3
"""Limpia los datos de prueba que dejaron las auditorias (prefijos AUD-, AUD2-, aud-ops-u).

Solo desarrollo. Por omision es un DRY-RUN: calcula y muestra todo lo que se borraria
y no escribe nada. Con --aplicar borra, en UNA transaccion, y si algo falla no queda nada.

Como decide que borrar
----------------------
1. RAICES: filas cuyo texto empieza con AUD-/AUD2- en las columnas de RAICES (abajo).
2. DEPENDIENTES: todo lo que apunte a esas filas por una llave foranea, recursivamente
   (hijos primero). Lo que cuelga de un dato de prueba es dato de prueba.
3. AVISOS: notificaciones cuyo destino (voucher/proyect/purchase_order) se borra.
4. Un PARACAIDAS: si el cierre arrastra una fila de `user` que no sea una cuenta aud-*,
   o mas filas de las esperadas en tablas de catalogo, el script se detiene y lo dice.

Respaldo: antes de --aplicar haz `pg_dump` (ver el comando que imprime el script).

Uso:
    docker compose exec -T backend python scripts/limpiar_datos_aud.py            # dry-run
    docker compose exec -T backend python scripts/limpiar_datos_aud.py --aplicar
"""
import argparse
import pathlib
import sys
from collections import defaultdict, deque

RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import text

from app.models.session import transaction_context

PREFIJO = r"^(aud2?-|aud-ops-u)"

# (tabla, columna): donde un valor que empieza con AUD marca la fila como de prueba.
RAICES = [
    ("appointment", "guest_name"), ("appointment_type", "name"),
    ("calendar_profile", "calendar_code"), ("customer_contact", "full_name"),
    ("customer_supplier", "name"), ("incident", "note"),
    ("inventory_asset", "asset_tag"), ("invoice", "folio"), ("invoice", "note"),
    ("invoice", "nombre_receptor"), ("invoice", "nombre_emisor"),
    ("location", "location_description"), ("product", "product_code"),
    ("proyect", "title"), ("proyect_material_need", "description"),
    ("purchase_order", "description"), ("purchase_order_line", "description"),
    ("supervisor_activity_log", "description"), ("task", "title"),
    ("task", "task_description"), ("task_note", "task_note_description"),
    ("user", "username"), ("notification", "message"),
]
# Notificaciones que apuntan a algo que se borra.
DESTINOS = {"voucher": "incident", "proyect": "proyect", "purchase_order": "purchase_order"}
# Tablas de las que el cierre NO debe arrastrar filas inesperadas.
VIGILADAS = {"user": "username", "customer_supplier": "name", "status": None, "permission": None}


def _pk_de(db, tabla):
    fila = db.execute(text("""
        select a.attname from pg_index i join pg_attribute a
          on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
        where i.indrelid = cast(:t as regclass) and i.indisprimary"""), {"t": '"%s"' % tabla}).all()
    return [f[0] for f in fila]


def _llaves_foraneas(db):
    """[(hija, col_hija, padre, col_padre)] de las FK de una sola columna."""
    return db.execute(text("""
        select cl.relname, a.attname, cp.relname, ap.attname
        from pg_constraint c
        join pg_class cl on cl.oid = c.conrelid
        join pg_class cp on cp.oid = c.confrelid
        join pg_namespace n on n.oid = cl.relnamespace and n.nspname = 'public'
        join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
        join pg_attribute ap on ap.attrelid = c.confrelid and ap.attnum = c.confkey[1]
        where c.contype = 'f' and array_length(c.conkey, 1) = 1""")).all()


def calcular(db):
    fks = _llaves_foraneas(db)
    hijos_de = defaultdict(list)
    for hija, ch, padre, cp in fks:
        hijos_de[padre].append((hija, ch, cp))

    conjunto = defaultdict(set)      # tabla -> {ctid como texto}
    cola = deque()

    def agregar(tabla, ctids):
        nuevos = set(ctids) - conjunto[tabla]
        if nuevos:
            conjunto[tabla] |= nuevos
            cola.append((tabla, nuevos))

    for tabla, col in RAICES:
        filas = db.execute(text(
            'select ctid::text from "%s" where "%s" ~* :p' % (tabla, col)), {"p": PREFIJO}).all()
        agregar(tabla, [f[0] for f in filas])

    def expandir():
        while cola:
            padre, ctids = cola.popleft()
            for hija, ch, cp in hijos_de.get(padre, []):
                filas = db.execute(text(
                    'select h.ctid::text from "%s" h where h."%s" in '
                    '(select p."%s" from "%s" p where p.ctid = any(cast(:c as tid[])))'
                    % (hija, ch, cp, padre)), {"c": "{" + ",".join('"%s"' % c for c in ctids) + "}"}).all()
                agregar(hija, [f[0] for f in filas])

    expandir()

    # Padres que se quedarian sin ningun hijo vivo: una orden de compra cuyas renglones
    # se borran TODAS era de prueba aunque su descripcion no lo diga.
    if conjunto.get("purchase_order_line"):
        huerfanas = db.execute(text("""
            select po.ctid::text from purchase_order po
            where exists (select 1 from purchase_order_line l where l.id_purchase_order = po.id_purchase_order
                          and l.ctid = any(cast(:c as tid[])))
              and not exists (select 1 from purchase_order_line l where l.id_purchase_order = po.id_purchase_order
                              and not (l.ctid = any(cast(:c as tid[]))))"""),
            {"c": "{" + ",".join('"%s"' % c for c in conjunto["purchase_order_line"]) + "}"}).all()
        agregar("purchase_order", [f[0] for f in huerfanas])
        expandir()

    # Avisos cuyo destino se borra.
    for entidad, tabla in DESTINOS.items():
        pk = _pk_de(db, tabla)
        if len(pk) != 1 or not conjunto.get(tabla):
            continue
        filas = db.execute(text(
            "select n.ctid::text from notification n where n.target_entity = :e and n.target_id in "
            '(select p."%s" from "%s" p where p.ctid = any(cast(:c as tid[])))' % (pk[0], tabla)),
            {"e": entidad, "c": "{" + ",".join('"%s"' % c for c in conjunto[tabla]) + "}"}).all()
        agregar("notification", [f[0] for f in filas])
    return fks, conjunto


def paracaidas(db, conjunto):
    problemas = []
    filas = db.execute(text(
        'select username from "user" where ctid = any(cast(:c as tid[]))'),
        {"c": "{" + ",".join('"%s"' % c for c in conjunto.get("user", [])) + "}"}).all() \
        if conjunto.get("user") else []
    for (usuario,) in filas:
        if not str(usuario or "").lower().startswith("aud"):
            problemas.append("el cierre arrastra al usuario real %r" % usuario)
    for tabla in ("status", "permission"):
        if conjunto.get(tabla):
            problemas.append("el cierre arrastra %d fila(s) de catalogo `%s`" % (len(conjunto[tabla]), tabla))
    return problemas


def orden_de_borrado(fks, tablas):
    """Hijos antes que padres (Kahn sobre las tablas implicadas; autorreferencias se ignoran)."""
    tablas = set(tablas)
    hijos = defaultdict(set)   # padre -> hijas
    grado = {t: 0 for t in tablas}
    for hija, _, padre, _ in fks:
        if hija in tablas and padre in tablas and hija != padre and hija not in hijos[padre]:
            hijos[padre].add(hija)
            grado[hija] += 0
    # una tabla se borra cuando ya se borraron todas sus hijas
    pendientes = {t: {h for h in hijos[t]} for t in tablas}
    orden, listos = [], deque(sorted(t for t in tablas if not pendientes[t]))
    while listos:
        t = listos.popleft()
        orden.append(t)
        for p, hs in pendientes.items():
            if t in hs:
                hs.discard(t)
                if not hs and p not in orden and p not in listos:
                    listos.append(p)
    restantes = [t for t in tablas if t not in orden]
    return orden + sorted(restantes)   # ciclos: se intentan al final, con reintentos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true", help="borra de verdad (sin esto es dry-run)")
    args = ap.parse_args()

    with transaction_context() as db:
        fks, conjunto = calcular(db)
        total = sum(len(v) for v in conjunto.values())
        print("MODO:", "APLICAR" if args.aplicar else "DRY-RUN (no se escribe nada)")
        print("Tablas implicadas: %d, filas: %d" % (len([t for t in conjunto if conjunto[t]]), total))
        for tabla in sorted(conjunto, key=lambda t: -len(conjunto[t])):
            if conjunto[tabla]:
                print("  %-34s %6d" % (tabla, len(conjunto[tabla])))

        problemas = paracaidas(db, conjunto)
        if problemas:
            print("\nSE DETIENE (paracaidas):")
            for p in problemas:
                print("  -", p)
            sys.exit(2)

        if not args.aplicar:
            print("\nNada se escribio. Respalda y repite con --aplicar:")
            print("  docker compose exec -T db sh -c 'pg_dump -U $POSTGRES_USER $POSTGRES_DB' > respaldo_antes_de_limpiar_aud.sql")
            db.rollback()
            return

        orden = orden_de_borrado(fks, [t for t in conjunto if conjunto[t]])
        pendientes = {t: set(conjunto[t]) for t in orden}
        for _ in range(5):                      # reintentos por ciclos entre tablas
            avance = False
            for tabla in orden:
                if not pendientes[tabla]:
                    continue
                arr = "{" + ",".join('"%s"' % c for c in pendientes[tabla]) + "}"
                sp = db.begin_nested()
                try:
                    r = db.execute(text('delete from "%s" where ctid = any(cast(:c as tid[]))' % tabla), {"c": arr})
                    sp.commit()
                    pendientes[tabla] = set()
                    avance = True
                    print("  borradas %6d de %s" % (r.rowcount, tabla))
                except Exception as e:
                    sp.rollback()
                    ultimo = str(e).splitlines()[0]
            if not any(pendientes.values()):
                break
            if not avance:
                restantes = {t: len(v) for t, v in pendientes.items() if v}
                raise SystemExit("No se pudo borrar %s (ultimo error: %s). No se guardo nada." % (restantes, ultimo))
        print("Hecho: transaccion confirmada.")


if __name__ == "__main__":
    main()
