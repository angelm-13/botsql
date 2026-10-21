"""Verificacion MANUAL de la pestana «Asistencias» del selector de KPI. Corre DENTRO del contenedor del backend, sobre una COPIA de la base.

    python receta_pestana_asistencias.py preparar     # rol adm_asistencias (lee kpi_definition, alcance Todos) + usuario de prueba
    python receta_pestana_asistencias.py verificar    # pide el catalogo de KPIs como el superusuario y como adm_asistencias (solo lectura)

Entre las dos se corre la herramienta REAL que asigna los siete KPIs al rol (no esta reescrita aqui):

    python -m scripts.seed_kpi_permissions --perfil comala

Lee docs/verificaciones/README.md antes de correrlo: la receta completa (con la copia de la base) esta ahi.

Que comprueba `verificar`: lo que el selector recibiria. Llama a `GET /kpi_definition/` con la aplicacion REAL (permisos y plan incluidos) y agrupa lo que
vuelve por la pestana del selector (`grupo`, y si no tiene, `modulo`; la misma regla que `pestanaDeKpi` en el frontend). No dibuja nada: el dibujo del selector
lo cubren las pruebas de node (`frontend/src/kpi/`).

Seguridad: `preparar` ESCRIBE, asi que se niega a correr si `RECETA_BASE_ESPERADA` no esta definida o no coincide con la base a la que apunta la conexion.
No existe `limpiar`: la copia se borra completa al terminar.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

import bcrypt
from sqlalchemy import select

from app import create_app
from app.kpis.modulos import checadas
from app.kpis.registry import KPI_REGISTRY
from app.models.entity_permission import EntityPermission
from app.models.permission import Permission
from app.models.session import engine, transaction_context
from app.models.user import User
from app.routes.auth import _bootstrap_admin_username, _issue_token, _user_payload

ROL = "adm_asistencias"
USUARIO = "asist.prueba"
CLAVE = "Prueba2026!"
SIETE = {kpi.clave for kpi in checadas.definiciones()}


def confirmar_base(escribe):
    """Imprime la base en la que va a trabajar. Si va a escribir, exige RECETA_BASE_ESPERADA y que coincida."""
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    esperada = os.environ.get("RECETA_BASE_ESPERADA")
    if escribe and not esperada:
        sys.exit("ABORTADO: `preparar` escribe y exige RECETA_BASE_ESPERADA (el nombre de la COPIA). No se hizo nada.")
    if esperada and esperada != base:
        sys.exit(f"ABORTADO: se esperaba la base '{esperada}' y la conexion apunta a '{base}'. No se hizo nada.")


def preparar():
    confirmar_base(escribe=True)
    with transaction_context() as db:
        admin = db.scalars(select(User).where(User.username == _bootstrap_admin_username())).first()
        if admin is None:
            sys.exit("ABORTADO: no hay usuario administrador de arranque en esta base.")
        modelo = db.get(Permission, admin.id_permission)

        rol = db.scalars(select(Permission).where(Permission.permission_description == ROL)).first()
        if rol is None:
            rol = Permission(
                permission_description=ROL, created_by=1, authorized_by=modelo.authorized_by,
                id_department=modelo.id_department, id_subdepartment=modelo.id_subdepartment, id_level=modelo.id_level,
            )
            db.add(rol)
            db.flush()
        # Capa 1: leer kpi_definition con alcance Todos (con Propios o Mis grupos los KPIs por equipo responden 403).
        if db.scalars(select(EntityPermission).where(
            EntityPermission.id_permission == rol.id_permission, EntityPermission.entity_name == "kpi_definition",
        )).first() is None:
            db.add(EntityPermission(
                id_permission=rol.id_permission, entity_name="kpi_definition",
                scope_create=0, scope_read=4, scope_update=0, scope_delete=0, created_by=1,
            ))
        if db.scalars(select(User).where(User.username == USUARIO)).first() is None:
            db.add(User(
                username=USUARIO, password=bcrypt.hashpw(CLAVE.encode(), bcrypt.gensalt()).decode(),
                email=f"{USUARIO}@prueba.local", id_proyect=admin.id_proyect, id_permission=rol.id_permission,
                id_status=admin.id_status, user_type="employee", full_name="Asistencias Prueba",
                supervisor=admin.supervisor or admin.id_user, first_name="Asistencias", last_name_father="Prueba",
                last_name_mother="Copia", created_by=1,
            ))
        print(f"listo: rol '{ROL}' (id {rol.id_permission}) y usuario '{USUARIO}' (clave {CLAVE}).")
    print("Siguiente: python -m scripts.seed_kpi_permissions --perfil comala --dry-run   (y despues sin --dry-run)")


def catalogo_como(cliente, username):
    """`GET /kpi_definition/` como ese usuario, con un token como el que emite el login real."""
    with transaction_context() as db:
        usuario = db.scalars(select(User).where(User.username == username)).first()
        if usuario is None:
            sys.exit(f"ABORTADO: no existe el usuario '{username}'. Corre `preparar` primero.")
        token = _issue_token(_user_payload(usuario), 5)
    respuesta = cliente.get("/kpi_definition/", headers={"Authorization": f"Bearer {token}"})
    if respuesta.status_code != 200:
        sys.exit(f"ABORTADO: GET /kpi_definition/ como {username} dio {respuesta.status_code}: {respuesta.get_data(as_text=True)[:200]}")
    return respuesta.get_json()["items"]


def pestanas(items):
    """Pestana del selector -> cuantos KPIs (la regla de `pestanaDeKpi`: `grupo`, y si no, `modulo`)."""
    return dict(Counter(item.get("grupo") or item["modulo"] for item in items))


def verificar():
    confirmar_base(escribe=False)
    cliente = create_app().test_client()
    fallos = []

    def comprobar(condicion, texto):
        print(("  ok   " if condicion else "  FALLA ") + texto)
        if not condicion:
            fallos.append(texto)

    print(f"\n[superusuario: {_bootstrap_admin_username()}]")
    items = catalogo_como(cliente, _bootstrap_admin_username())
    mapa = pestanas(items)
    print("  pestanas:", mapa)
    comprobar(len(items) == len(KPI_REGISTRY), f"ve los {len(KPI_REGISTRY)} KPIs del registry (vio {len(items)})")
    comprobar(mapa.get("asistencias") == 7, "Asistencias trae 7")
    comprobar(mapa.get("operaciones") == 12, "Operaciones trae 12")
    comprobar(all(i["modulo"] == "operaciones" for i in items if i["clave"] in SIETE), "los siete siguen con modulo=operaciones")

    print(f"\n[rol limitado: {USUARIO} ({ROL})]")
    items = catalogo_como(cliente, USUARIO)
    mapa = pestanas(items)
    print("  pestanas:", mapa)
    comprobar({i["clave"] for i in items} == SIETE, f"ve exactamente los siete de checadas (vio {len(items)})")
    comprobar(mapa == {"asistencias": 7}, "una sola pestana: Asistencias con 7 (sin Operaciones ni Variables)")
    comprobar(all(i["modulo"] == "operaciones" and i["grupo"] == "asistencias" for i in items), "modulo=operaciones y grupo=asistencias en todos")

    print("\nTODO EN ORDEN" if not fallos else f"\n{len(fallos)} COMPROBACION(ES) FALLARON")
    sys.exit(1 if fallos else 0)


def main():
    comandos = {"preparar": preparar, "verificar": verificar}
    if len(sys.argv) != 2 or sys.argv[1] not in comandos:
        sys.exit(f"uso: python receta_pestana_asistencias.py {{{'|'.join(comandos)}}}")
    comandos[sys.argv[1]]()


if __name__ == "__main__":
    main()
