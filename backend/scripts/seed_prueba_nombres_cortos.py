"""Seis empleados de PRUEBA para ver nombres cortos en las graficas de KPIs. SOLO la base local de desarrollo.

    docker compose exec backend python -m scripts.seed_prueba_nombres_cortos               # dry-run: imprime y NO escribe
    docker compose exec backend python -m scripts.seed_prueba_nombres_cortos --aplicar     # escribe
    docker compose exec backend python -m scripts.seed_prueba_nombres_cortos --deshacer            # dry-run del borrado
    docker compose exec backend python -m scripts.seed_prueba_nombres_cortos --deshacer --aplicar  # borra solo lo marcado

Mismo mecanismo que `docs/verificaciones/receta_datos_demo.py` (los "PRUEBA Persona NN"): SQL directo, el rol «PRUEBA sin permisos», `username`
propio, `is_employee`, membresia en `nm_team_user`. Solo `full_name` va lleno (como en los datos reales): `first_name` y los apellidos quedan vacios.

Guardia (la misma de la receta): se niega a seguir si corre dentro de un pod, si el host no es `db` o si la base no es `tyakxa_erp`/`tyakxa_verif`.

Marca, para poder deshacer: `username` con prefijo `prueba_nombres_`, correo `@prueba.local` e `incident.external_source = 'PRUEBA-NOMBRES'`.
`--deshacer` borra solo filas con esas marcas (y los snapshots por persona de esos usuarios).

Las incidencias son «resuelta» (y unas pocas «abierta»/«en_proceso», sin `close_date`, para que los porcentajes difieran), con `incident_date` en los ultimos 30 dias (el KPI `incidentes_resueltos_por_empleado` agrupa por `incident_date`) y un
`close_date` unas horas despues. Sin coordenadas, para que no se confundan con una checada. Todas las fechas salen de `app/utils/tiempo.py`.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.models.session import engine, transaction_context  # noqa: E402
from app.utils.tiempo import ahora_negocio, hoy_negocio, pared_a_utc  # noqa: E402

PREFIJO_USUARIO = "prueba_nombres_"
DOMINIO = "@prueba.local"
FUENTE = "PRUEBA-NOMBRES"
BASES_PERMITIDAS = ("tyakxa_erp", "tyakxa_verif")
HOST_COMPOSE = "db"
ROL = "PRUEBA sin permisos"
EQUIPO_POR_OMISION = "PRUEBA Manzanillo 1"
TIPO_POR_OMISION = "Extraviado"
DIAS = 30

# (clave, full_name, cuantas incidencias resueltas, estatus de las NO resueltas): cantidades distintas entre personas y, con las no
# resueltas de 01, 03 y 05, porcentajes distintos en `incidentes_resueltos_por_empleado` (60 %, 100 %, 88.9 %, 100 %, 75 %, 100 %).
# 05 y 06 comparten forma corta («Luis Fernando Torres»): prueban la colision.
PERSONAS = (
    ("01", "María José Ramírez", 3, ("abierta", "en_proceso")),
    ("02", "María José Ramírez Soto", 5, ()),
    ("03", "Carlos Alberto Mendoza Ruiz", 8, ("abierta",)),
    ("04", "Miguel Hidalgo y Costilla", 4, ()),
    ("05", "Luis Fernando Torres Vega", 6, ("abierta", "en_proceso")),
    ("06", "Luis Fernando Torres Ríos", 7, ()),
)


def confirmar_base():
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        sys.exit("ABORTADO: esto corre dentro de un pod. Solo para el docker-compose local. No se hizo nada.")
    if host != HOST_COMPOSE:
        sys.exit(f"ABORTADO: el host debe ser '{HOST_COMPOSE}' (el del compose local) y es '{host}'. No se hizo nada.")
    if base not in BASES_PERMITIDAS:
        sys.exit(f"ABORTADO: la base debe ser una de {BASES_PERMITIDAS} y es '{base}'. No se hizo nada.")
    esperada = os.environ.get("RECETA_BASE_ESPERADA")
    if esperada and esperada != base:
        sys.exit(f"ABORTADO: se esperaba la base '{esperada}' y la conexion apunta a '{base}'. No se hizo nada.")


def incidencias_de(indice: int, cuantas: int, hoy):
    """`[(incident_date, close_date)]` en hora de pared: repartidas en los ultimos 30 dias, deterministas y distintas entre personas."""
    paso = max(1, (DIAS - 1) // cuantas)
    filas = []
    for k in range(cuantas):
        dias_antes = min(DIAS - 1, 1 + k * paso + (indice % paso))
        inicio = datetime.combine(hoy - timedelta(days=dias_antes), time(8 + (k * 2 + indice) % 9, (15 * (k + indice)) % 60))
        filas.append((inicio, inicio + timedelta(hours=1 + (k + indice) % 6)))
    return filas


def pendientes_de(indice: int, estatus, hoy):
    """`[(estatus, incident_date)]` de las NO resueltas (sin `close_date`), en dias distintos a los de las resueltas en lo posible."""
    return [(estado, datetime.combine(hoy - timedelta(days=2 + 3 * j + indice), time(9 + (j + indice) % 8, 30)))
            for j, estado in enumerate(estatus)]


def _uno(db, sql, **parametros):
    return db.execute(text(sql), parametros).scalar()


def plan(db, equipo: str, tipo: str):
    """Lo que se insertaria, o por que no se puede. Solo lee."""
    id_rol = _uno(db, "select id_permission from permission where permission_description = :d", d=ROL)
    id_equipo = _uno(db, "select id_team from team where team_description = :d and deletion_date is null", d=equipo)
    id_tipo = _uno(db, "select id_incident_type from incident_type where incident_type_description = :d", d=tipo)
    faltan = [nombre for nombre, valor in (("rol «" + ROL + "»", id_rol), ("equipo «" + equipo + "»", id_equipo), ("tipo «" + tipo + "»", id_tipo)) if valor is None]
    if faltan:
        sys.exit("ABORTADO: no existe " + ", ".join(faltan) + ". No se hizo nada.")
    hoy = hoy_negocio()
    existentes = {
        u: _uno(db, 'select id_user from "user" where username = :u', u=u)
        for u in (PREFIJO_USUARIO + clave for clave, *_ in PERSONAS)
    }
    for username, id_user in existentes.items():
        if id_user is not None and not _uno(db, 'select 1 from "user" where id_user = :i and email like :e', i=id_user, e="%" + DOMINIO):
            sys.exit(f"ABORTADO: ya existe un usuario '{username}' que NO es de esta prueba. No se toca.")
    return id_rol, id_equipo, id_tipo, hoy, existentes


def imprimir_plan(equipo, tipo, id_rol, id_equipo, id_tipo, hoy, existentes):
    print(f"\nrol: «{ROL}» (id {id_rol}) | equipo: «{equipo}» (id {id_equipo}) | tipo de incidencia: «{tipo}» (id {id_tipo})")
    print(f"hoy del negocio: {hoy} | ventana: {hoy - timedelta(days=DIAS - 1)} ... {hoy}")
    total = 0
    for indice, (clave, nombre, cuantas, pendientes) in enumerate(PERSONAS):
        username = PREFIJO_USUARIO + clave
        estado = "YA EXISTE (se omite)" if existentes[username] else "se crea"
        print(f"\n  user  {username:22s} {username + DOMINIO:36s} full_name={nombre!r}  first_name/apellidos=vacios  is_employee  [{estado}]")
        print(f"        nm_team_user -> «{equipo}»")
        filas = incidencias_de(indice, cuantas, hoy)
        total += cuantas
        print(f"        {cuantas} incidencias 'resuelta' (external_source={FUENTE!r}):")
        for inicio, cierre in filas:
            print(f"          incident_date={inicio:%Y-%m-%d %H:%M}  close_date={cierre:%Y-%m-%d %H:%M}")
        for estatus, inicio in pendientes_de(indice, pendientes, hoy):
            total += 1
            print(f"          NO resuelta '{estatus}': incident_date={inicio:%Y-%m-%d %H:%M}  close_date=NULL")
        print(f"        porcentaje resuelto esperado: {100 * cuantas / (cuantas + len(pendientes)):.1f} %")
    print(f"\nTOTAL: {len(PERSONAS)} user, {len(PERSONAS)} nm_team_user, {total} incident.")


def sembrar(equipo: str, tipo: str, aplicar: bool):
    confirmar_base()
    with transaction_context() as db:
        id_rol, id_equipo, id_tipo, hoy, existentes = plan(db, equipo, tipo)
    imprimir_plan(equipo, tipo, id_rol, id_equipo, id_tipo, hoy, existentes)
    if not aplicar:
        print("\nDRY-RUN: no se escribio nada. Para aplicar: --aplicar")
        return
    ahora = ahora_negocio().replace(microsecond=0)
    alta = pared_a_utc(ahora - timedelta(days=DIAS + 5))
    with transaction_context() as db:
        for indice, (clave, nombre, cuantas, pendientes) in enumerate(PERSONAS):
            username = PREFIJO_USUARIO + clave
            if existentes[username] is not None:
                print(f"  {username}: ya existe, se omite")
                continue
            id_user = db.execute(text(
                'insert into "user" (full_name, username, email, is_employee, user_type, id_permission, creation_date) '
                "values (:n, :u, :e, true, 'employee', :r, :c) returning id_user"),
                {"n": nombre, "u": username, "e": username + DOMINIO, "r": id_rol, "c": alta}).scalar()
            db.execute(text("insert into nm_team_user (id_team, id_user, creation_date, last_update_date) values (:t, :u, :a, :a)"),
                       {"t": id_equipo, "u": id_user, "a": alta})
            for k, (inicio, cierre) in enumerate(incidencias_de(indice, cuantas, hoy), start=1):
                db.execute(text(
                    "insert into incident (incident_date, close_date, id_incident_type, note, id_user, incident_status, created_by, "
                    "creation_date, last_update_date, external_source) "
                    "values (:i, :c, :t, :n, :u, 'resuelta', :u, :cu, :lu, :f)"),
                    {"i": inicio, "c": cierre, "t": id_tipo, "n": f"{FUENTE} {nombre} #{k}", "u": id_user,
                     "cu": pared_a_utc(inicio), "lu": pared_a_utc(cierre), "f": FUENTE})
            for k, (estatus, inicio) in enumerate(pendientes_de(indice, pendientes, hoy), start=cuantas + 1):
                db.execute(text(
                    "insert into incident (incident_date, id_incident_type, note, id_user, incident_status, created_by, "
                    "creation_date, last_update_date, external_source) "
                    "values (:i, :t, :n, :u, :s, :u, :cu, :cu, :f)"),
                    {"i": inicio, "t": id_tipo, "n": f"{FUENTE} {nombre} #{k}", "u": id_user, "s": estatus,
                     "cu": pared_a_utc(inicio), "f": FUENTE})
            print(f"  {username}: creado (id_user {id_user}) con {cuantas} resueltas y {len(pendientes)} sin resolver")
    print(f"\nListo. Siguiente: recalcular {hoy - timedelta(days=DIAS - 1)} ... {hoy} con scripts/recalculate_kpi_snapshots_range.py")


def deshacer(aplicar: bool):
    confirmar_base()
    with transaction_context() as db:
        ids = [fila[0] for fila in db.execute(text(
            'select id_user from "user" where username like :u and email like :e order by id_user'),
            {"u": PREFIJO_USUARIO + "%", "e": "%" + DOMINIO}).all()]
        cuentas = {
            "incident (external_source = PRUEBA-NOMBRES)": _uno(db, "select count(*) from incident where external_source = :f", f=FUENTE),
            "nm_team_user de esos usuarios": _uno(db, "select count(*) from nm_team_user where id_user = any(:u)", u=ids or [-1]),
            "kpi_snapshot por persona de esos usuarios": _uno(
                db, "select count(*) from kpi_snapshot where (dimension_key->>'id_user') = any(:u)", u=[str(i) for i in ids] or ["-1"]),
            "user (prefijo + correo marcados)": len(ids),
        }
        print("\nSe borraria:")
        for nombre, n in cuentas.items():
            print(f"  {nombre:50s} {n}")
        if not aplicar:
            print("\nDRY-RUN: no se borro nada. Para borrar: --deshacer --aplicar")
            return
        db.execute(text("delete from incident where external_source = :f"), {"f": FUENTE})
        db.execute(text("delete from nm_team_user where id_user = any(:u)"), {"u": ids or [-1]})
        db.execute(text("delete from kpi_snapshot where (dimension_key->>'id_user') = any(:u)"), {"u": [str(i) for i in ids] or ["-1"]})
        db.execute(text('delete from "user" where id_user = any(:u)'), {"u": ids or [-1]})
    print("\nBorrado. Los snapshots AGREGADOS (sin id_user) de esos dias se corrigen al recalcular el rango.")


def main():
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--aplicar", action="store_true", help="escribe (sin esto es dry-run)")
    analizador.add_argument("--deshacer", action="store_true", help="borra solo lo marcado")
    analizador.add_argument("--equipo", default=EQUIPO_POR_OMISION)
    analizador.add_argument("--tipo", default=TIPO_POR_OMISION, help="descripcion de un incident_type que ya exista")
    argumentos = analizador.parse_args()
    if argumentos.deshacer:
        deshacer(argumentos.aplicar)
    else:
        sembrar(argumentos.equipo, argumentos.tipo, argumentos.aplicar)


if __name__ == "__main__":
    main()
