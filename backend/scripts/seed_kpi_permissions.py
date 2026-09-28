"""Siembra idempotente de `nm_permission_kpi`: que KPIs ve cada rol.

Por que existe
--------------
Un usuario que no es superusuario solo ve un KPI si pasan dos capas:

1. **Acceso al modulo `kpis`** (`entity_permission` sobre `kpi_definition`,
   etc.). Esa capa vive en `ROLES` (`app/modules/registry.py`) y la siembra
   la matriz de permisos; este script NO la toca, solo avisa si falta.
2. **`puede_ver` por KPI** (`nm_permission_kpi`). Es la que siembra este
   script, a partir de `ASIGNACIONES` y no de INSERTs a mano.

`nm_permission_kpi` no la toca ninguna migracion (a diferencia de
`entity_permission`, cuyas matrices reaplicadas en cada arranque borran filas
con created_by=1), asi que lo que siembra este script sobrevive a `db-migrate`
y a los reinicios del backend. Verificado en local.

Que hace y que no
-----------------
* Roles por NOMBRE (`permission.permission_description`), nunca por id: los
  ids cambian de una base a otra.
* Un rol que no existe se reporta y se salta; nunca se crea.
* Idempotente: solo inserta el par (rol, KPI) que falta. Una fila viva no se
  modifica, y una fila con `deletion_date` no se reactiva (mismo criterio que
  la matriz de `entity_permission`).
* OJO: desmarcar un KPI en `/kpi_permissions` BORRA la fila (DELETE fisico,
  `BaseService.delete`), no la da de baja. Para el script eso es igual a "nunca
  asignado", asi que volver a correrlo la reasigna. Para quitar un KPI de forma
  permanente hay que sacarlo tambien de `ASIGNACIONES`.
* Aditivo: nunca quita un KPI que un rol ya tenga y que no este aqui.
* Valida ANTES de escribir: claves de KPI que no existen en `KPI_REGISTRY`, y
  roles acotados a proyecto que reciban un KPI con `alcance_proyecto=False`
  (verian datos de toda la empresa). Con cualquier error no escribe nada.

Uso
---
    python -m scripts.seed_kpi_permissions --perfil adser --dry-run
    python -m scripts.seed_kpi_permissions --perfil adser

En k8s (ver docs/despliegues/2026-09-25_kpis_adser_permisos.md):

    kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run

Codigos de salida: 0 bien; 1 error de validacion (no se escribio nada);
2 algun rol no existe (lo demas si se aplico, o se mostro en --dry-run).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.kpis.registry import KPI_REGISTRY  # noqa: E402
from app.models.entity_permission import EntityPermission  # noqa: E402
from app.models.kpi_definition import KpiDefinition  # noqa: E402
from app.models.nm_permission_kpi import NmPermissionKpi  # noqa: E402
from app.models.permission import Permission  # noqa: E402
from app.models.session import transaction_context  # noqa: E402


@dataclass(frozen=True)
class AsignacionRol:
    rol: str                   # permission.permission_description, tal cual
    acotado_a_proyecto: bool   # True: no puede recibir KPIs con alcance_proyecto=False
    kpis: tuple[str, ...]      # claves de KPI_REGISTRY


# Por perfil de despliegue: cada cliente decide que roles ven que KPIs, y un
# perfil no hereda nada de otro. Agregar un cliente es agregar una entrada.
ASIGNACIONES = {
    "adser": (
        # En Adser solo Administrator (taroj) recibe KPIs; Almacenista se queda
        # sin cambios. Administrator ya tiene el modulo `kpis` en ROLES.
        #
        # `articulos_bajo_stock` queda FUERA a proposito: el almacen de Adser
        # es de herramientas individuales, casi toda la existencia real es 1
        # -- "bajo stock" no significa nada ahi. Lo que le importa a Adser es
        # cuantas incidencias se abren/cierran, cuanto material esta prestado
        # (vales de almacen, `nm_incident_product`) y en que estado esta cada
        # renglon -- de ahi los 4 KPIs nuevos.
        #
        # `vales_vencidos_por_responsable` sigue FUERA por el mismo motivo de
        # siempre: `nm_incident_product.due_date` viene vacio en los datos de
        # Adser -- saldria siempre en cero. Se agrega cuando due_date se
        # capture.
        #
        # `material_prestado_actual` SI se agrega: aunque `nm_incident_product.
        # start_date`/`due_date` siguen vacios en Adser, este KPI se diseno
        # para no depender de ellos -- usa `Incident.incident_date` como fecha
        # de prestamo (confirmado real contra `migrate_adser.py`, viene de
        # `fecha_incidente` de origen sin sentinel), que si esta poblado.
        AsignacionRol(
            rol="Administrator",
            acotado_a_proyecto=False,
            kpis=(
                "material_prestado_actual",
                "incidentes_resueltos_por_empleado",
                "incidencias_abiertas_por_empleado",
                "incidencias_pendientes",
                "incidencias_abiertas_vs_cerradas",
                "material_por_estado",
            ),
        ),
    ),
}


@dataclass
class Accion:
    rol: str
    clave: str
    estado: str      # "insertar" | "ya_existe" | "retirado" | "puede_ver_false"
    id_permission: int | None = None
    id_kpi_definition: int | None = None


@dataclass
class Plan:
    acciones: list
    roles_faltantes: list
    avisos: list

    @property
    def por_insertar(self):
        return [a for a in self.acciones if a.estado == "insertar"]


def validar(asignaciones) -> list[str]:
    """Errores que impiden correr, sin tocar la base."""
    alcance_por_clave = {kpi.clave: kpi.alcance_proyecto for kpi in KPI_REGISTRY}
    errores = []
    roles_vistos = set()
    for asignacion in asignaciones:
        if asignacion.rol in roles_vistos:
            errores.append(f"El rol '{asignacion.rol}' aparece dos veces en la asignacion.")
        roles_vistos.add(asignacion.rol)
        if len(set(asignacion.kpis)) != len(asignacion.kpis):
            errores.append(f"El rol '{asignacion.rol}' repite un KPI en su lista.")
        for clave in asignacion.kpis:
            if clave not in alcance_por_clave:
                errores.append(f"El KPI '{clave}' (rol '{asignacion.rol}') no existe en KPI_REGISTRY.")
            elif asignacion.acotado_a_proyecto and not alcance_por_clave[clave]:
                errores.append(
                    f"El rol '{asignacion.rol}' esta acotado a proyecto y no puede recibir "
                    f"'{clave}': ese KPI no tiene alcance por proyecto (alcance_proyecto=False), "
                    "asi que le mostraria datos de toda la empresa."
                )
    return errores


def planear(session, asignaciones) -> Plan:
    """Que haria el script, sin escribir nada."""
    ids_rol = {
        descripcion: id_permission
        for id_permission, descripcion in session.execute(
            select(Permission.id_permission, Permission.permission_description)
            .where(Permission.deletion_date.is_(None))
        )
    }
    ids_kpi = {
        clave: id_kpi
        for id_kpi, clave in session.execute(
            select(KpiDefinition.id_kpi_definition, KpiDefinition.clave)
            .where(KpiDefinition.deletion_date.is_(None))
        )
    }

    acciones, roles_faltantes, avisos = [], [], []
    for asignacion in asignaciones:
        id_permission = ids_rol.get(asignacion.rol)
        if id_permission is None:
            roles_faltantes.append(asignacion.rol)
            continue

        lectura = session.scalar(
            select(EntityPermission.scope_read).where(
                EntityPermission.id_permission == id_permission,
                EntityPermission.entity_name == "kpi_definition",
                EntityPermission.deletion_date.is_(None),
            )
        )
        if not lectura:
            avisos.append(
                f"El rol '{asignacion.rol}' no tiene lectura de kpi_definition (capa 1): no vera "
                "ningun KPI aunque tenga puede_ver. Esa capa se da en ROLES (app/modules/registry.py)."
            )

        for clave in asignacion.kpis:
            id_kpi = ids_kpi.get(clave)
            if id_kpi is None:
                avisos.append(
                    f"El KPI '{clave}' no esta en kpi_definition de esta base (la siembra del "
                    "registry no ha corrido); se omite."
                )
                continue
            filas = session.scalars(
                select(NmPermissionKpi).where(
                    NmPermissionKpi.id_permission == id_permission,
                    NmPermissionKpi.id_kpi_definition == id_kpi,
                )
            ).all()
            viva = next((f for f in filas if f.deletion_date is None), None)
            if viva is not None:
                estado = "ya_existe" if viva.puede_ver else "puede_ver_false"
            elif filas:
                estado = "retirado"
            else:
                estado = "insertar"
            acciones.append(Accion(asignacion.rol, clave, estado, id_permission, id_kpi))
    return Plan(acciones, roles_faltantes, avisos)


def aplicar(session, plan: Plan) -> int:
    for accion in plan.por_insertar:
        session.add(NmPermissionKpi(
            id_permission=accion.id_permission,
            id_kpi_definition=accion.id_kpi_definition,
            puede_ver=True,
            created_by=1,
        ))
    session.flush()
    return len(plan.por_insertar)


_DESCRIPCION_ESTADO = {
    "insertar": "INSERTAR",
    "ya_existe": "ya existe, sin cambios",
    "retirado": "dado de baja por un administrador; NO se reactiva",
    "puede_ver_false": "existe con puede_ver=false; NO se toca",
}


def imprimir(plan: Plan, dry_run: bool) -> None:
    for accion in plan.acciones:
        print(f"  {accion.rol:<20} {accion.clave:<45} {_DESCRIPCION_ESTADO[accion.estado]}")
    for rol in plan.roles_faltantes:
        print(f"  ROL INEXISTENTE: '{rol}' no existe en esta base; se omite (no se crea).")
    for aviso in plan.avisos:
        print(f"  AVISO: {aviso}")
    verbo = "Se insertarian" if dry_run else "Insertadas"
    print(f"{verbo}: {len(plan.por_insertar)} fila(s) en nm_permission_kpi.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Siembra nm_permission_kpi por rol y perfil de despliegue.")
    parser.add_argument("--perfil", required=True, choices=sorted(ASIGNACIONES), help="perfil de despliegue (cliente)")
    parser.add_argument("--dry-run", action="store_true", help="muestra lo que haria sin escribir nada")
    args = parser.parse_args(argv)
    asignaciones = ASIGNACIONES[args.perfil]

    errores = validar(asignaciones)
    if errores:
        for error in errores:
            print(f"ERROR: {error}")
        print("No se escribio nada.")
        return 1

    print(f"Perfil '{args.perfil}'{' (dry-run: no se escribe nada)' if args.dry_run else ''}:")
    with transaction_context() as session:
        plan = planear(session, asignaciones)
        if not args.dry_run:
            aplicar(session, plan)
    imprimir(plan, args.dry_run)
    return 2 if plan.roles_faltantes else 0


if __name__ == "__main__":
    sys.exit(main())
