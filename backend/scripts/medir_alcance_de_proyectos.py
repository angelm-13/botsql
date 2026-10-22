#!/usr/bin/env python3
"""Mide, SIN ESCRIBIR NADA, que proyectos veria cada rol con la regla nueva.

Por que existe
--------------
Desde el 2026-10-16 la celda `proyect.scope_read` del Gestor de roles y
permisos MANDA sobre lo que ve un rol sin capacidad de proyecto (ni
`project_authorization` ni `project_execution`): Todos ve todos los proyectos,
Mis grupos suma a su equipo, Propios solo lo propio. Antes el codigo ignoraba
"Todos" ahi -esos roles solo veian lo que ellos mismos creaban-, asi que un rol
sembrado en Todos "no se notaba".

Con la regla nueva, un rol que hoy esta en Todos y que NO deberia ver los
proyectos de los demas (tipicamente Supervisor) pasaria a verlos. Este script
lista, por rol, la celda de `proyect` y marca los que cambiarian, para pasarlos
a Propios en el Gestor ANTES de promover el codigo. No cambia nada: eso se hace
desde el Gestor, que es quien manda.

Que revisa
----------
Por cada rol vivo: sus 4 celdas de `proyect` (crear, leer, actualizar,
eliminar), si tiene las capacidades `project_authorization`, `project_execution`
y `project_supply`, y cuantos usuarios vivos lo llevan. Marca "CAMBIA" cuando el
rol no tiene autorizar ni ejecutar y su lectura incluye Todos: esos son los que
veran todo con el codigo nuevo. Tambien marca la EDICION ajena: con
`scope_update` en Todos pueden editar borradores de otros.

Uso (dentro del backend del ambiente; solo lectura):
    python scripts/medir_alcance_de_proyectos.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

ALCANCE = {0: "Sin acceso", 1: "Propios", 2: "Mis grupos", 4: "Todos"}


def etiqueta(valor) -> str:
    valor = int(valor or 0)
    if valor in ALCANCE:
        return ALCANCE[valor]
    # Union de bits (3, 5, 6, 7): el bit 4 domina.
    return "Todos" if valor & 4 else "+".join(n for b, n in ((1, "Propios"), (2, "Mis grupos")) if valor & b)


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def main():
    conn = conectar()
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id_permission, p.permission_description,
                   (SELECT count(*) FROM "user" u
                     WHERE u.id_permission = p.id_permission AND u.deletion_date IS NULL) AS usuarios
              FROM permission p
             WHERE p.deletion_date IS NULL
             ORDER BY p.id_permission
            """
        )
        roles = cur.fetchall()

        cur.execute(
            "SELECT id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete "
            "FROM entity_permission WHERE deletion_date IS NULL "
            "AND entity_name IN ('proyect', 'project_authorization', 'project_execution', 'project_supply')"
        )
        celdas: dict[int, dict] = {}
        for id_permission, entidad, c, r, u, d in cur.fetchall():
            celdas.setdefault(id_permission, {})[entidad] = (c, r, u, d)

        print(f"{'rol':<22}{'usuarios':>9}  {'crear':<11}{'leer':<11}{'actualizar':<12}{'eliminar':<11}capacidades -> efecto")
        print('-' * 118)
        cambian = 0
        for id_permission, nombre, usuarios in roles:
            mias = celdas.get(id_permission, {})
            if 'proyect' not in mias and not any(k.startswith('project_') for k in mias):
                continue
            c, r, u, d = mias.get('proyect', (0, 0, 0, 0))
            tiene = {k: int(mias.get(k, (0, 0, 0, 0))[1] or 0) != 0
                     for k in ('project_authorization', 'project_execution', 'project_supply')}
            caps = ",".join(k.replace('project_', '') for k, v in tiene.items() if v) or "-"
            efecto = ""
            if not tiene['project_authorization'] and not tiene['project_execution'] and int(r or 0) != 0:
                if int(r) & 4:
                    efecto = "CAMBIA: vera TODOS los proyectos"
                    cambian += usuarios
                if int(u or 0) & 4:
                    efecto += (" | " if efecto else "") + "podra editar borradores ajenos"
            print(f"{nombre:<22}{usuarios:>9}  {etiqueta(c):<11}{etiqueta(r):<11}{etiqueta(u):<12}{etiqueta(d):<11}{caps}  {efecto}")

        print()
        if cambian:
            print(f"{cambian} usuario(s) vivo(s) pasarian a ver todos los proyectos con el codigo nuevo.")
            print("Si no deben, pasa `proyect` (leer y actualizar) de esos roles a Propios en el Gestor ANTES de promover.")
        else:
            print("Ningun rol cambia de alcance con el codigo nuevo.")
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
