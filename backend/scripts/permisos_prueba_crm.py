"""Da a UN rol de prueba local `puede_ver` sobre los seis KPIs de la pestana CRM. SOLO la base local de desarrollo.

    docker compose exec backend python -m scripts.permisos_prueba_crm                          # dry-run: imprime y NO escribe
    docker compose exec backend python -m scripts.permisos_prueba_crm --aplicar                # escribe
    docker compose exec backend python -m scripts.permisos_prueba_crm --deshacer               # dry-run del retiro
    docker compose exec backend python -m scripts.permisos_prueba_crm --deshacer --aplicar     # retira esas seis filas
    docker compose exec backend python -m scripts.permisos_prueba_crm --rol "Gerente Comercial"   # otro rol local

Es la capa 2 del permiso de un KPI (`nm_permission_kpi.puede_ver`): usa el mismo `planear`/`aplicar` de `seed_kpi_permissions.py`
(roles por NOMBRE, un rol que no existe se reporta y no se crea, no reactiva lo que un administrador dio de baja). Solo toca
`nm_permission_kpi`; NO escribe `entity_permission`: esa es la capa 1 y la maneja el Gestor de roles y permisos. El script AVISA
si al rol le falta:

  * `kpi_definition` con lectura (sin ella el rol no ve ningun KPI),
  * `kpi_dashboard` con lectura (sin ella no abre el Dashboard),
  * alcance TODOS en la lectura de `kpi_definition`: con Propios o Mis grupos la API responde 403 (motivo `scope`) a todo KPI que
    no sea por persona, y cinco de los seis lo son (`tareas_bloqueadas_por_responsable` es el unico por persona).

Por omision el rol es «PRUEBA sin permisos» (el de los usuarios `prueba.NN`); hoy NO tiene ninguna fila de `entity_permission`, asi que
antes hay que darle en el Gestor la lectura de `kpi_definition` y de `kpi_dashboard`, con alcance Todos.

Los seis KPIs son `alcance_proyecto=False`, asi que el rol NO puede estar acotado a un proyecto (`seed_kpi_permissions.validar` lo rechazaria).

Guardia (la misma de `seed_prueba_nombres_cortos.py`): se niega a seguir si corre dentro de un pod, si el host no es `db` o si la base
no es `tyakxa_erp`/`tyakxa_verif`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select  # noqa: E402

from app.models.entity_permission import EntityPermission  # noqa: E402
from app.models.kpi_definition import KpiDefinition  # noqa: E402
from app.models.nm_permission_kpi import NmPermissionKpi  # noqa: E402
from app.models.permission import Permission  # noqa: E402
from app.models.session import engine, transaction_context  # noqa: E402
from scripts.seed_kpi_permissions import AsignacionRol, aplicar, imprimir, planear, validar  # noqa: E402

BASES_PERMITIDAS = ("tyakxa_erp", "tyakxa_verif")
HOST_COMPOSE = "db"
ROL_POR_OMISION = "PRUEBA sin permisos"
SCOPE_TODOS = 4

SEIS_KPIS_DE_CRM = (
    "clientes_nuevos",
    "clientes_activos",
    "proyectos_por_estado_comercial",
    "proyectos_con_entrega_vencida",
    "tareas_por_estado",
    "tareas_bloqueadas_por_responsable",
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


def asignacion(rol):
    return AsignacionRol(rol=rol, acotado_a_proyecto=False, kpis=SEIS_KPIS_DE_CRM)


def avisos_de_capa_1(session, rol):
    """Lo que le falta al rol en `entity_permission` (capa 1) para que de verdad vea los KPIs. Solo lee."""
    id_permission = session.scalar(
        select(Permission.id_permission).where(Permission.permission_description == rol, Permission.deletion_date.is_(None))
    )
    if id_permission is None:
        return []
    avisos = []
    for entidad in ("kpi_definition", "kpi_dashboard"):
        lectura = session.scalar(select(EntityPermission.scope_read).where(
            EntityPermission.id_permission == id_permission, EntityPermission.entity_name == entidad,
            EntityPermission.deletion_date.is_(None),
        ))
        if not lectura:
            avisos.append(f"capa 1: al rol '{rol}' le falta la lectura de `{entidad}` (Gestor de roles y permisos, alcance Todos).")
        elif entidad == "kpi_definition" and lectura != SCOPE_TODOS:
            avisos.append(
                f"capa 1: la lectura de `kpi_definition` del rol '{rol}' no es Todos (es {lectura}): con Propios o Mis grupos cinco de "
                "los seis KPIs responden 403 con motivo `scope`."
            )
    return avisos


def conceder(rol, aplicar_cambios):
    errores = validar((asignacion(rol),))
    if errores:
        sys.exit("ERROR: " + " | ".join(errores) + " No se escribio nada.")
    with transaction_context() as session:
        plan = planear(session, (asignacion(rol),))
        plan.avisos.extend(avisos_de_capa_1(session, rol))
        if aplicar_cambios and not plan.roles_faltantes:
            aplicar(session, plan)
    imprimir(plan, dry_run=not aplicar_cambios)
    if not aplicar_cambios:
        print("\nDRY-RUN: no se escribio nada. Para aplicar: --aplicar")
    return 2 if plan.roles_faltantes else 0


def retirar(rol, aplicar_cambios):
    with transaction_context() as session:
        id_permission = session.scalar(
            select(Permission.id_permission).where(Permission.permission_description == rol, Permission.deletion_date.is_(None))
        )
        if id_permission is None:
            print(f"ROL INEXISTENTE: '{rol}' no existe en esta base. No se hizo nada.")
            return 2
        ids_kpi = list(session.scalars(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave.in_(SEIS_KPIS_DE_CRM))))
        filas = session.scalars(select(NmPermissionKpi).where(
            NmPermissionKpi.id_permission == id_permission, NmPermissionKpi.id_kpi_definition.in_(ids_kpi))).all()
        print(f"\nSe retirarian {len(filas)} fila(s) de nm_permission_kpi del rol '{rol}' (solo los seis KPIs de CRM).")
        if not aplicar_cambios:
            print("\nDRY-RUN: no se borro nada. Para retirar: --deshacer --aplicar")
            return 0
        session.execute(delete(NmPermissionKpi).where(
            NmPermissionKpi.id_permission == id_permission, NmPermissionKpi.id_kpi_definition.in_(ids_kpi)))
    print("\nRetiradas.")
    return 0


def main():
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--aplicar", action="store_true", help="escribe (sin esto es dry-run)")
    analizador.add_argument("--deshacer", action="store_true", help="retira las filas de esos seis KPIs para el rol")
    analizador.add_argument("--rol", default=ROL_POR_OMISION, help=f"permission.permission_description (por omision «{ROL_POR_OMISION}»)")
    argumentos = analizador.parse_args()
    confirmar_base()
    if argumentos.deshacer:
        return retirar(argumentos.rol, argumentos.aplicar)
    return conceder(argumentos.rol, argumentos.aplicar)


if __name__ == "__main__":
    sys.exit(main())
