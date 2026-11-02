"""Datos de PRUEBA de un coworking para ver los KPIs de la pestana CRM. SOLO la base local de desarrollo.

    docker compose exec backend python -m scripts.seed_prueba_crm_coworking               # dry-run: imprime y NO escribe
    docker compose exec backend python -m scripts.seed_prueba_crm_coworking --aplicar     # escribe
    docker compose exec backend python -m scripts.seed_prueba_crm_coworking --deshacer            # dry-run del borrado
    docker compose exec backend python -m scripts.seed_prueba_crm_coworking --deshacer --aplicar  # borra solo lo marcado

Que siembra (todo con nombres de coworking): 8 clientes «Inquilino 1»..«Inquilino 8» (`type='client'`, dados de alta en los
ultimos 60 dias) y un proveedor que NO es cliente; 12 proyectos «Oficina 1»..«Oficina 12» en distintos estados de taller y
comerciales, con fechas de entrega pasadas, futuras y vacias; y tareas de esas oficinas en todos los estados (y una sin estado),
repartidas entre los responsables. Los responsables NO se crean: son usuarios que ya existen (por omision los `prueba.NN`;
`--responsables 28,29,30` elige otros).

Lo que deben mostrar los KPIs con estos datos (los valores salen de `DATOS_DE_PRUEBA`; `test_seed_prueba_crm_coworking.py` los verifica):

    clientes_activos                 4   (Inquilino 1, 4, 5 y 7)
    proyectos_con_entrega_vencida    4   (Oficina 2, 5, 6 y 11)
    proyectos_por_estado_comercial   pendiente_orden_compra 3 (+1 el proyecto interno del admin), autorizado 4, cancelado 2, cobrado 3
    tareas_por_estado                pendiente 5, en_proceso 5, bloqueada 4, en_revision 2, terminada 5, cancelada 2, sin_estado 1
    tareas_bloqueadas_por_responsable   2 / 1 / 1 entre tres de los responsables
    clientes_nuevos                  8 altas repartidas en los ultimos 60 dias (rango recomendado: «ultimos 60 dias»)

Despues de sembrar hay que recalcular: `docker compose exec backend python -m scripts.recalculate_kpi_snapshots_range <inicio> <fin>`
(las fotos de proyectos, tareas y clientes activos solo se escriben para HOY; las altas de clientes, para cada dia del rango).

Guardia (la misma de `seed_prueba_nombres_cortos.py`): se niega a seguir si corre dentro de un pod, si el host no es `db` o si la
base no es `tyakxa_erp`/`tyakxa_verif`.

Marca, para poder deshacer: clientes con correo `@prueba-crm.local`, proyectos con `folio = 'PRUEBA-CRM'` y tareas con
`title = 'PRUEBA-CRM'`. `--deshacer` borra solo filas con esas marcas (primero las tareas, luego los proyectos y los clientes).
Es idempotente: si ya hay datos marcados, sembrar no vuelve a insertar.
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
from app.utils.tiempo import hoy_negocio, pared_a_utc  # noqa: E402

BASES_PERMITIDAS = ("tyakxa_erp", "tyakxa_verif")
HOST_COMPOSE = "db"
DOMINIO = "@prueba-crm.local"
MARCA = "PRUEBA-CRM"
ADMIN_ID = 1
USUARIO_POR_OMISION = "prueba.%"

# (nombre, tipo, dias desde el alta hasta hoy). El proveedor no es un cliente: ningun KPI de clientes lo cuenta.
CLIENTES = (
    ("Inquilino 1", "client", 58), ("Inquilino 2", "client", 50), ("Inquilino 3", "client", 41), ("Inquilino 4", "client", 33),
    ("Inquilino 5", "client", 24), ("Inquilino 6", "client", 15), ("Inquilino 7", "client", 8), ("Inquilino 8", "client", 2),
    ("Mobiliario Ofimex", "supplier", 70),
)

# (descripcion, indice de cliente, proyect_status, management_status, dias de entrega desde hoy: negativo = ya paso, None = sin fecha)
PROYECTOS = (
    ("Oficina 1", 0, "in_progress", "autorizado", 20),
    ("Oficina 2", 0, "waiting_material", "autorizado", -5),            # vencida
    ("Oficina 3", 1, "draft", "pendiente_orden_compra", None),
    ("Oficina 4", 2, "completed", "cobrado", -30),
    ("Oficina 5", 3, "blocked", "autorizado", -10),                    # vencida: un proyecto bloqueado cuenta
    ("Oficina 6", 4, "stopped", "autorizado", -3),                     # vencida: uno detenido cuenta
    ("Oficina 7", 4, "authorized", "pendiente_orden_compra", 10),
    ("Oficina 8", 5, "denied", "cancelado", -15),
    ("Oficina 9", 5, "in_progress", "cancelado", -2),                  # cancelada: no esta vencida
    ("Oficina 10", 6, "collected", "cobrado", -7),
    ("Oficina 11", 6, "submitted", "pendiente_orden_compra", -1),      # vencida
    ("Oficina 12", 7, "completed", "cobrado", None),
)

# (indice de proyecto, task_status, indice de responsable, descripcion). `None` en el estado = una tarea sin estado.
TAREAS = (
    (0, "pendiente", 0, "Instalar cableado de red"), (0, "en_proceso", 0, "Montar escritorios"),
    (0, "terminada", 1, "Pintar muros"), (1, "bloqueada", 0, "Esperar llegada de mamparas"),
    (1, "pendiente", 2, "Cotizar persianas"), (2, "pendiente", 1, "Definir distribucion"),
    (3, "terminada", 1, "Entrega de llaves"), (3, "terminada", 2, "Revision final de la oficina"),
    (4, "bloqueada", 0, "Permiso de la administracion del edificio"), (4, "en_proceso", 2, "Cambiar cerradura"),
    (5, "bloqueada", 1, "Falta contacto para la acometida"), (5, "en_revision", 1, "Validar planos de la oficina"),
    (6, "pendiente", 2, "Medir el espacio"), (6, "en_proceso", 0, "Compra de sillas"),
    (7, "cancelada", 2, "Cotizacion rechazada"), (8, "cancelada", 1, "Obra cancelada por el inquilino"),
    (8, "bloqueada", 2, "Retirar muebles"), (9, "terminada", 0, "Recoger llaves"),
    (9, "en_proceso", 1, "Limpieza final"), (10, "en_revision", 2, "Revisar acabados"),
    (10, "en_proceso", 0, "Instalar iluminacion"), (11, "terminada", 2, "Cierre administrativo"),
    (2, "pendiente", 1, "Reunion de arranque"), (10, None, 2, "Tarea capturada sin estado"),
)

# Lo que esta siembra deja a cada KPI (ver el docstring). Los verifica `tests/test_services/test_seed_prueba_crm_coworking.py`.
DATOS_DE_PRUEBA = {
    "clientes_activos": 4,
    "proyectos_con_entrega_vencida": 4,
    "proyectos_por_estado_comercial": {"pendiente_orden_compra": 3, "autorizado": 4, "cancelado": 2, "cobrado": 3},
    "tareas_por_estado": {
        "pendiente": 5, "en_proceso": 5, "bloqueada": 4, "en_revision": 2, "terminada": 5, "cancelada": 2, "sin_estado": 1,
    },
}


def confirmar_base():
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        sys.exit("ABORTADO: esto corre dentro de un pod. Solo para el docker-compose local. No se hizo nada.")
    if host != HOST_COMPOSE:
        sys.exit(f"ABORTADO: el host debe ser '{HOST_COMPOSE}' (el del compose local) y es '{host}'. No se hizo nada.")
    if base not in BASES_PERMITIDAS:
        sys.exit(f"ABORTADO: la base debe ser una de {BASES_PERMITIDAS} y es '{base}'. No se hizo nada.")


def _uno(db, sql, **parametros):
    return db.execute(text(sql), parametros).scalar()


def _cuentas_marcadas(db):
    return {
        "clientes": _uno(db, "select count(*) from customer_supplier where email like :e", e="%" + DOMINIO),
        "proyectos": _uno(db, "select count(*) from proyect where folio = :m", m=MARCA),
        "tareas": _uno(db, "select count(*) from task where title = :m", m=MARCA),
    }


def elegir_responsables(db, pedidos):
    """Los usuarios que seran responsables: los pedidos, o los `prueba.NN` de siempre. Ya deben existir."""
    if pedidos:
        filas = db.execute(text('select id_user, full_name from "user" where id_user = any(:i) and deletion_date is null order by id_user'),
                           {"i": pedidos}).all()
        faltan = sorted(set(pedidos) - {fila[0] for fila in filas})
        if faltan:
            sys.exit(f"ABORTADO: no existen (o estan de baja) los usuarios {faltan}. No se hizo nada.")
    else:
        filas = db.execute(text(
            'select id_user, full_name from "user" where username like :u and deletion_date is null order by id_user limit 3'),
            {"u": USUARIO_POR_OMISION}).all()
    if len(filas) < 3:
        sys.exit("ABORTADO: hacen falta al menos 3 responsables; usa --responsables 28,29,30. No se hizo nada.")
    return [(fila[0], fila[1]) for fila in filas]


def imprimir_plan(hoy, responsables, marcadas):
    print(f"\nhoy del negocio: {hoy}")
    print("responsables (ya existen, no se crean): " + ", ".join(f"{i} {n!r}" for i, n in responsables))
    print(f"\n  {len(CLIENTES)} clientes ({sum(1 for c in CLIENTES if c[1] == 'client')} client + "
          f"{sum(1 for c in CLIENTES if c[1] == 'supplier')} supplier), correo `...{DOMINIO}`:")
    for nombre, tipo, dias in CLIENTES:
        print(f"    {nombre:20s} {tipo:9s} alta {hoy - timedelta(days=dias)}")
    print(f"\n  {len(PROYECTOS)} proyectos (folio {MARCA!r}):")
    for descripcion, cliente, estado, comercial, entrega in PROYECTOS:
        fecha = f"{hoy + timedelta(days=entrega)}" if entrega is not None else "sin fecha"
        print(f"    {descripcion:11s} de {CLIENTES[cliente][0]:12s} taller={estado:17s} comercial={comercial:23s} entrega={fecha}")
    print(f"\n  {len(TAREAS)} tareas (title {MARCA!r}):")
    por_estado: dict = {}
    for _, estado, _, _ in TAREAS:
        por_estado[estado or "sin estado"] = por_estado.get(estado or "sin estado", 0) + 1
    print("    " + ", ".join(f"{estado} {n}" for estado, n in por_estado.items()))
    if any(marcadas.values()):
        print(f"\n  YA HAY datos marcados {marcadas}: sembrar no inserta nada (usa --deshacer primero si quieres rehacerlos).")
    else:
        print(f"\nTOTAL: {len(CLIENTES)} customer_supplier, {len(PROYECTOS)} proyect, {len(TAREAS)} task.")


def insertar(db, responsables, hoy):
    """Escribe los datos marcados y regresa `(ids de clientes, ids de proyectos, ids de tareas)`. Sin guardia: la pone `sembrar`."""
    ids_responsables = [i for i, _ in responsables]
    ids_clientes = []
    for nombre, tipo, dias in CLIENTES:
        alta = pared_a_utc(datetime.combine(hoy - timedelta(days=dias), time(10, 0)))
        ids_clientes.append(db.execute(text(
            "insert into customer_supplier (name, type, email, id_user, created_by, creation_date, last_update_date) "
            "values (:n, :t, :e, :u, :a, :c, :c) returning id_customer_supplier"),
            {"n": nombre, "t": tipo, "e": nombre.lower().replace(" ", "") + DOMINIO, "u": ids_responsables[0], "a": ADMIN_ID, "c": alta},
        ).scalar())
    ids_proyectos = []
    for indice, (descripcion, cliente, estado, comercial, entrega) in enumerate(PROYECTOS):
        alta = pared_a_utc(datetime.combine(hoy - timedelta(days=60 - 4 * indice), time(11, 0)))
        ids_proyectos.append(db.execute(text(
            "insert into proyect (id_customer_supplier, leader, id_supervisor, proyect_description, proyect_status, "
            "management_status, delivery_date, folio, created_by, creation_date, last_update_date) "
            "values (:c, :l, :l, :d, :s, :m, :f, :folio, :a, :cd, :cd) returning id_proyect"),
            {"c": ids_clientes[cliente], "l": ids_responsables[indice % len(ids_responsables)], "d": descripcion, "s": estado,
             "m": comercial, "f": hoy + timedelta(days=entrega) if entrega is not None else None, "folio": MARCA,
             "a": ADMIN_ID, "cd": alta},
        ).scalar())
    ids_tareas = []
    for indice, (proyecto, estado, responsable, descripcion) in enumerate(TAREAS):
        alta = pared_a_utc(datetime.combine(hoy - timedelta(days=30 - indice), time(9, 0)))
        ids_tareas.append(db.execute(text(
            "insert into task (owner, dependency, validation, task_description, task_status, id_proyect, title, created_by, "
            "creation_date, last_update_date) values (:o, 0, :a, :d, :s, :p, :m, :a, :c, :c) returning id_task"),
            {"o": ids_responsables[responsable], "a": ADMIN_ID, "d": f"{descripcion} ({PROYECTOS[proyecto][0]})", "s": estado,
             "p": ids_proyectos[proyecto], "m": MARCA, "c": alta},
        ).scalar())
    return ids_clientes, ids_proyectos, ids_tareas


def borrar(db):
    """Borra solo lo marcado: tareas, luego proyectos, luego clientes. Regresa cuantas filas borro de cada tabla."""
    tareas = db.execute(text("delete from task where title = :m"), {"m": MARCA}).rowcount
    ids = [fila[0] for fila in db.execute(text("select id_proyect from proyect where folio = :m"), {"m": MARCA}).all()]
    if ids:
        db.execute(text("delete from proyect_event where id_proyect = any(:i)"), {"i": ids})
    proyectos = db.execute(text("delete from proyect where folio = :m"), {"m": MARCA}).rowcount
    clientes = db.execute(text("delete from customer_supplier where email like :e"), {"e": "%" + DOMINIO}).rowcount
    return {"tareas": tareas, "proyectos": proyectos, "clientes": clientes}


def sembrar(pedidos, aplicar):
    confirmar_base()
    hoy = hoy_negocio()
    with transaction_context() as db:
        responsables = elegir_responsables(db, pedidos)
        marcadas = _cuentas_marcadas(db)
    imprimir_plan(hoy, responsables, marcadas)
    if any(marcadas.values()):
        return
    if not aplicar:
        print("\nDRY-RUN: no se escribio nada. Para aplicar: --aplicar")
        return
    with transaction_context() as db:
        clientes, proyectos, tareas = insertar(db, responsables, hoy)
    print(f"\nListo: {len(clientes)} clientes, {len(proyectos)} proyectos, {len(tareas)} tareas.")
    print(f"Siguiente: recalcular {hoy - timedelta(days=60)} ... {hoy} con scripts/recalculate_kpi_snapshots_range.py")


def deshacer(aplicar):
    confirmar_base()
    with transaction_context() as db:
        marcadas = _cuentas_marcadas(db)
        print(f"\nSe borraria: {marcadas}")
        if not aplicar:
            print("\nDRY-RUN: no se borro nada. Para borrar: --deshacer --aplicar")
            return
        borradas = borrar(db)
    print(f"\nBorrado: {borradas}. Los snapshots ya calculados se corrigen al recalcular el rango.")


def main():
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--aplicar", action="store_true", help="escribe (sin esto es dry-run)")
    analizador.add_argument("--deshacer", action="store_true", help="borra solo lo marcado")
    analizador.add_argument("--responsables", type=lambda texto: [int(i) for i in texto.split(",")],
                            help="ids de usuarios que ya existen (por omision, los prueba.NN); al menos 3")
    argumentos = analizador.parse_args()
    if argumentos.deshacer:
        deshacer(argumentos.aplicar)
    else:
        sembrar(argumentos.responsables, argumentos.aplicar)


if __name__ == "__main__":
    main()
