"""Lleva a una base la configuracion de permisos de uno o mas roles, tal como esta en otra.

Para que lo ajustado en el Gestor de roles de un ambiente (p. ej. tyakxa-dev) llegue a otro
(p. ej. adser-prod) sin repetirlo a mano. Un cambio de codigo no lo lleva: esa configuracion
vive en `entity_permission` y `nm_field_permission`, no en el registro.

El archivo de entrada es un JSON con, por rol (nombre EXACTO del rol destino), sus entidades
y sus campos VIVOS:

    {"roles": {"Gerente Comercial": {
        "entidades": [{"entity_name": ..., "scope_create": ..., "scope_read": ...,
                       "scope_update": ..., "scope_delete": ..., "menu_location": ...,
                       "menu_group": ..., "menu_group_icon": ..., "menu_label": ...,
                       "menu_order": ...}],
        "campos": [{"table_name": ..., "field_name": ..., "control_type": ...}]}}}

Los roles y las entidades se buscan por NOMBRE, los campos por (tabla, campo): los ids no son
los mismos entre ambientes.

Que hace (el rol destino queda igual que el origen):
  * lo que viene en el archivo se agrega, se actualiza o se reactiva;
  * lo que el rol tiene vivo y NO viene en el archivo se da de BAJA (baja logica: la fila se
    queda con `deletion_date`, no se borra; es reversible desde el respaldo);
  * toda fila que toca queda con `ajustado_por_gestor` = ahora, como si la hubiera movido el
    Gestor: el trigger "el Gestor manda" descarta cualquier UPDATE de migracion sobre una fila
    ajustada que no cambie esa columna, asi que sin esa marca las migraciones la revertirian.

Seguridad:
  * Por omision es una SIMULACION: calcula y muestra todo, y deshace la transaccion.
    `--aplicar` confirma.
  * Antes de tocar nada escribe un respaldo CSV de las filas actuales de esos roles
    (`--respaldo-dir`), con el que se puede volver atras.
  * Una sola transaccion: si algo falla no queda nada a medias.
  * Es idempotente: una segunda pasada no cambia nada.

Uso (dentro del contenedor del backend, con las variables DB_* del entorno):

    python scripts/aplicar_permisos_de_roles.py roles.json                  # simulacion
    python scripts/aplicar_permisos_de_roles.py roles.json --aplicar
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import psycopg2

CAMPOS_ENTIDAD = ("scope_create", "scope_read", "scope_update", "scope_delete",
                  "menu_location", "menu_group", "menu_group_icon", "menu_label", "menu_order")


def conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def buscar_rol(cur, nombre: str) -> int:
    """El rol vivo por nombre, sin importar mayusculas. Debe haber exactamente uno."""
    cur.execute(
        "SELECT id_permission FROM permission "
        "WHERE lower(permission_description) = lower(%s) AND deletion_date IS NULL",
        (nombre,))
    filas = cur.fetchall()
    if len(filas) != 1:
        raise SystemExit(
            f"El rol '{nombre}' debe existir una sola vez y vivo; hay {len(filas)}. "
            "Corre antes las migraciones de la version que lo crea.")
    return filas[0][0]


def respaldar(cur, ids_rol: dict[str, int], destino: str) -> list[str]:
    os.makedirs(destino, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ids = list(ids_rol.values())
    escritos = []
    for tabla in ("entity_permission", "nm_field_permission"):
        cur.execute(f"SELECT * FROM {tabla} WHERE id_permission = ANY(%s) ORDER BY 1", (ids,))
        columnas = [c.name for c in cur.description]
        ruta = os.path.join(destino, f"respaldo_roles_{marca}_{tabla}.csv")
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(columnas)
            w.writerows(cur.fetchall())
        escritos.append(ruta)
    return escritos


def aplicar_entidades(cur, id_rol: int, entidades: list[dict]) -> dict:
    cur.execute(
        "SELECT entity_name, deletion_date, " + ", ".join(CAMPOS_ENTIDAD) +
        " FROM entity_permission WHERE id_permission = %s", (id_rol,))
    existentes = {fila[0]: fila for fila in cur.fetchall()}
    pedidas = {e["entity_name"]: e for e in entidades}
    cuenta = {"agrega": [], "cambia": [], "reactiva": [], "baja": [], "igual": []}

    for nombre, e in pedidas.items():
        valores = tuple(e.get(c) for c in CAMPOS_ENTIDAD)
        fila = existentes.get(nombre)
        if fila is None:
            cur.execute(
                "INSERT INTO entity_permission (id_permission, entity_name, "
                + ", ".join(CAMPOS_ENTIDAD) +
                ", created_by, creation_date, last_update_date, ajustado_por_gestor) VALUES (%s, %s, "
                + ", ".join(["%s"] * len(CAMPOS_ENTIDAD)) + ", 1, now(), now(), now())",
                (id_rol, nombre, *valores))
            cuenta["agrega"].append(nombre)
            continue
        vivo = fila[1] is None
        if vivo and tuple(fila[2:]) == valores:
            cuenta["igual"].append(nombre)
            continue
        cur.execute(
            "UPDATE entity_permission SET " + ", ".join(f"{c} = %s" for c in CAMPOS_ENTIDAD) +
            ", deletion_date = NULL, last_update_date = now(), ajustado_por_gestor = now() "
            "WHERE id_permission = %s AND entity_name = %s",
            (*valores, id_rol, nombre))
        cuenta["cambia" if vivo else "reactiva"].append(nombre)

    for nombre, fila in existentes.items():
        if fila[1] is None and nombre not in pedidas:
            cur.execute(
                "UPDATE entity_permission SET deletion_date = now(), last_update_date = now(), "
                "ajustado_por_gestor = now() WHERE id_permission = %s AND entity_name = %s",
                (id_rol, nombre))
            cuenta["baja"].append(nombre)
    return cuenta


def aplicar_campos(cur, id_rol: int, campos: list[dict]) -> dict:
    """Deja UNA fila viva por campo pedido, con su control, y ninguna para el resto.

    `nm_field_permission` NO tiene restriccion unica por (campo, rol) y en la practica hay
    varias filas por par (las bajas y altas repetidas del Gestor y de las resiembras: en
    tyakxa-dev un rol llega a miles de bajas). Por eso se trabaja siempre por clave primaria:
    un UPDATE por (campo, rol) reactivaria TODAS las repetidas y dejaria varias vivas.
    """
    cur.execute("SELECT id_field, table_name, field_name FROM field WHERE deletion_date IS NULL")
    id_de_campo = {(t, f): i for i, t, f in cur.fetchall()}
    cur.execute(
        "SELECT id_nm_field_permission, id_field, deletion_date, control_type "
        "FROM nm_field_permission WHERE id_permission = %s ORDER BY id_nm_field_permission",
        (id_rol,))
    filas_por_campo: dict[int, list] = {}
    for fila in cur.fetchall():
        filas_por_campo.setdefault(fila[1], []).append(fila)
    cuenta = {"agrega": 0, "cambia": 0, "reactiva": 0, "baja": 0, "repetida": 0, "igual": 0,
              "sin_campo": []}
    pedidos = set()

    def baja_por_id(id_fila):
        cur.execute(
            "UPDATE nm_field_permission SET deletion_date = now(), last_update_date = now(), "
            "ajustado_por_gestor = now() WHERE id_nm_field_permission = %s", (id_fila,))

    for c in campos:
        id_field = id_de_campo.get((c["table_name"], c["field_name"]))
        if id_field is None:
            cuenta["sin_campo"].append(f'{c["table_name"]}.{c["field_name"]}')
            continue
        pedidos.add(id_field)
        control = None if c.get("control_type") is None else str(c["control_type"])
        filas = filas_por_campo.get(id_field, [])
        vivas = [f for f in filas if f[2] is None]
        if vivas:
            conservar = vivas[-1]  # la mas reciente; las demas son repetidas
            for repetida in vivas[:-1]:
                baja_por_id(repetida[0])
                cuenta["repetida"] += 1
            if conservar[3] != control:
                cur.execute(
                    "UPDATE nm_field_permission SET control_type = %s, last_update_date = now(), "
                    "ajustado_por_gestor = now() WHERE id_nm_field_permission = %s",
                    (control, conservar[0]))
                cuenta["cambia"] += 1
            elif not vivas[:-1]:
                cuenta["igual"] += 1
        elif filas:
            # Sin ninguna viva: se reactiva la mas reciente (las otras bajas se quedan).
            cur.execute(
                "UPDATE nm_field_permission SET control_type = %s, deletion_date = NULL, "
                "last_update_date = now(), ajustado_por_gestor = now() "
                "WHERE id_nm_field_permission = %s", (control, filas[-1][0]))
            cuenta["reactiva"] += 1
        else:
            cur.execute(
                "INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by, "
                "creation_date, last_update_date, ajustado_por_gestor) "
                "VALUES (%s, %s, %s, 1, now(), now(), now())", (id_field, id_rol, control))
            cuenta["agrega"] += 1

    for id_field, filas in filas_por_campo.items():
        if id_field in pedidos:
            continue
        for fila in filas:
            if fila[2] is None:
                baja_por_id(fila[0])
                cuenta["baja"] += 1
    return cuenta


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archivo", help="JSON con la configuracion de los roles")
    parser.add_argument("--aplicar", action="store_true", help="confirma los cambios (sin esto es simulacion)")
    parser.add_argument("--respaldo-dir", default="/tmp", help="donde escribir el respaldo CSV")
    args = parser.parse_args()

    with open(args.archivo, encoding="utf-8-sig") as f:
        roles = json.load(f)["roles"]

    conn = conectar()
    try:
        cur = conn.cursor()
        ids = {nombre: buscar_rol(cur, nombre) for nombre in roles}
        print("Roles destino:", ", ".join(f"{n} (id {i})" for n, i in ids.items()))
        for ruta in respaldar(cur, ids, args.respaldo_dir):
            print("Respaldo:", ruta)

        for nombre, id_rol in ids.items():
            ent = aplicar_entidades(cur, id_rol, roles[nombre].get("entidades", []))
            cam = aplicar_campos(cur, id_rol, roles[nombre].get("campos", []))
            print(f"\n== {nombre}")
            print("  entidades: " + ", ".join(f"{k} {len(v)}" for k, v in ent.items()))
            for k in ("agrega", "reactiva", "cambia", "baja"):
                if ent[k]:
                    print(f"    {k}: {', '.join(sorted(ent[k]))}")
            print("  campos: " + ", ".join(
                f"{k} {v if not isinstance(v, list) else len(v)}" for k, v in cam.items()))
            if cam["sin_campo"]:
                print("    campos del origen que este ambiente no tiene:", ", ".join(cam["sin_campo"][:15]))

        if args.aplicar:
            conn.commit()
            print("\nAPLICADO.")
        else:
            conn.rollback()
            print("\nSIMULACION: no se cambio nada. Repite con --aplicar para confirmar.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
