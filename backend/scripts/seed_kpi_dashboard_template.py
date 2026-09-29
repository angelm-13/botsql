"""Plantilla de tablero de KPIs para un usuario: el tablero de Adser, ya armado.

Por que existe
--------------
Un usuario nuevo abre el Dashboard y ve un tablero vacio: tiene que armar a
mano cada grafico, en el editor. Para Adser el primer tablero es siempre el
mismo -que se abre, que se cierra, cuanto material esta prestado y en que
estado-, asi que se siembra ya hecho, con los mismos widgets que crearia el
editor (mismo servicio, mismos parametros, incluido el rango relativo).

Que hace y que no
-----------------
* Crea, para UN usuario (`--usuario`, `taroj` por omision), un tablero privado
  con 5 widgets. Los de serie llevan un rango RELATIVO (`parametros.rango_relativo`)
  y, ademas, la foto de las fechas de hoy, exactamente como lo guarda el
  editor: el Dashboard recalcula las fechas cada vez que se abre. La tabla de
  un KPI "vivo" no lleva rango: solo guarda su ancho (`{"columnas": 2}`).
* AVISO sobre la tabla "Material prestado ahora": depende de
  `incident.incident_date` (la fecha del vale). NO correr en adser-prod hasta que
  Alan confirme, con una consulta de solo lectura, que esa fecha es confiable en
  lo migrado. Mientras tanto, `--sin-tabla` crea los otros 4 widgets.
* Idempotente: si el tablero (mismo nombre, mismo dueno) ya existe lo reusa, y
  un widget (mismo tipo de grafica y mismos KPIs) que ya este en el tablero no
  se vuelve a crear. Nunca modifica ni borra nada: si alguien cambio el rango de
  un widget, la plantilla lo respeta. Si alguien BORRO un widget de la
  plantilla, volver a correrla lo crea otra vez.
* Valida ANTES de escribir: el usuario debe existir y ver cada KPI de la
  plantilla (`nm_permission_kpi`, o ser superusuario). Con cualquier problema no
  escribe nada; el remedio de los permisos es
  `python -m scripts.seed_kpi_permissions --perfil adser`.
* Crea los widgets con `KpiDashboardWidgetService.create_widget`, el mismo camino
  que la API: no se salta ninguna validacion.

Uso
---
    python -m scripts.seed_kpi_dashboard_template --dry-run
    python -m scripts.seed_kpi_dashboard_template
    python -m scripts.seed_kpi_dashboard_template --usuario otro --nombre "Mi tablero"

En k8s (ver docs/despliegues/2026-09-29_kpis_dashboard_adser.md):

    kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --dry-run
    kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template

Codigos de salida: 0 bien; 1 error de validacion o permisos (no se escribio
nada); 2 el usuario no existe.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.kpis.registry import KPI_POR_CLAVE  # noqa: E402
from app.models.kpi_dashboard import KpiDashboard  # noqa: E402
from app.models.kpi_dashboard_widget import KpiDashboardWidget  # noqa: E402
from app.models.kpi_dashboard_widget_kpi import KpiDashboardWidgetKpi  # noqa: E402
from app.models.kpi_definition import KpiDefinition  # noqa: E402
from app.models.session import transaction_context  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routes.auth import _user_payload  # noqa: E402
from app.services.kpi_dashboard_service import KpiDashboardService  # noqa: E402
from app.services.kpi_dashboard_widget_service import KpiDashboardWidgetService  # noqa: E402
from app.utils.auth import has_kpi_permission  # noqa: E402
from app.utils.errors import AppError  # noqa: E402

USUARIO_POR_OMISION = "taroj"
NOMBRE_TABLERO = "Operación Adser"


@dataclass(frozen=True)
class WidgetPlantilla:
    clave_kpi: str
    tipo_grafica: str
    # Vacio solo para un KPI "vivo" (no tiene periodo).
    rango_relativo: str = ""
    # Contra el periodo inmediatamente anterior...
    comparar_anterior: bool = False
    # ...o contra el mismo rango N dias atras ("hoy contra hace 30 dias").
    comparar_desfase_dias: int = 0
    # Ancho en la cuadricula (2 = doble). Solo lo guarda una tabla; 1 = como los widgets de siempre.
    columnas: int = 1


# La plantilla. Cada rango es de los que ofrece el editor (RANGOS_RELATIVOS en
# frontend/src/kpi/kpiRango.js) y cada tipo de grafica esta entre las
# `graficas_permitidas` de su KPI (lo comprueba `validar`).
PLANTILLA = (
    # Cuantas incidencias siguen sin resolver hoy, contra el mismo dia de hace 30.
    WidgetPlantilla("incidencias_pendientes", "numero", "hoy", comparar_desfase_dias=30),
    # Cuantas se abren y cuantas se cierran, por dia, en lo que va del ano. Un
    # rango corto sale vacio en Adser: el ultimo vale migrado es del 15 de
    # agosto y no hay capturas nuevas.
    WidgetPlantilla("incidencias_abiertas_vs_cerradas", "barras", "este_anio"),
    # Quien es el responsable de las incidencias abiertas, en lo que va del ano.
    WidgetPlantilla("incidencias_abiertas_por_empleado", "barras", "este_anio"),
    # Material prestado sin devolver AHORA. KPI "vivo": sin rango, de ancho doble (parametros = {"columnas": 2}).
    # Depende de incident_date: ver el AVISO al inicio de este archivo.
    WidgetPlantilla("material_prestado_actual", "tabla", columnas=2),
    # En que estado esta el material de los vales, hoy.
    WidgetPlantilla("material_por_estado", "dona", "hoy"),
)

RANGOS_RELATIVOS = ("hoy", "7_dias", "30_dias", "90_dias", "este_mes", "mes_anterior", "este_anio")


# --- fechas: las mismas cuentas que frontend/src/kpi/kpiRango.js ---------------

def resolver_rango_relativo(clave: str, hoy: date) -> tuple[date, date]:
    """(inicio, fin) de un rango relativo. "N dias" cuenta HOY como uno de los N."""
    if clave == "hoy":
        return hoy, hoy
    if clave in ("7_dias", "30_dias", "90_dias"):
        return hoy - timedelta(days=int(clave.split("_")[0]) - 1), hoy
    if clave == "este_mes":
        return hoy.replace(day=1), hoy
    if clave == "mes_anterior":
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if clave == "este_anio":
        return date(hoy.year, 1, 1), hoy
    raise ValueError(f"rango relativo desconocido: {clave!r}")


def periodo_anterior(inicio: date, fin: date) -> tuple[date, date]:
    """El periodo inmediatamente anterior y de la misma duracion."""
    dias = (fin - inicio).days + 1
    fin_anterior = inicio - timedelta(days=1)
    return fin_anterior - timedelta(days=dias - 1), fin_anterior


def parametros_del_widget(widget: WidgetPlantilla, hoy: date) -> dict:
    """Los `parametros` tal como los guarda el editor para un rango relativo:
    la instruccion (`rango_relativo`) mas la foto de las fechas de hoy."""
    if not widget.rango_relativo:
        # Un KPI "vivo" no guarda periodo; lo unico que lleva es su ancho, y solo si es doble.
        return {"columnas": widget.columnas} if widget.tipo_grafica == "tabla" and widget.columnas == 2 else {}
    inicio, fin = resolver_rango_relativo(widget.rango_relativo, hoy)
    parametros = {
        "rango_relativo": widget.rango_relativo,
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
    }
    if widget.comparar_desfase_dias:
        dias = timedelta(days=widget.comparar_desfase_dias)
        parametros["comparar_desfase_dias"] = widget.comparar_desfase_dias
        parametros["fecha_inicio_b"] = (inicio - dias).isoformat()
        parametros["fecha_fin_b"] = (fin - dias).isoformat()
    elif widget.comparar_anterior:
        inicio_b, fin_b = periodo_anterior(inicio, fin)
        parametros["comparar_anterior"] = True
        parametros["fecha_inicio_b"] = inicio_b.isoformat()
        parametros["fecha_fin_b"] = fin_b.isoformat()
    return parametros


# --- validacion y plan ---------------------------------------------------------

def validar(plantilla=PLANTILLA) -> list[str]:
    """Errores de la plantilla en si (antes de mirar ninguna base)."""
    errores = []
    for widget in plantilla:
        kpi = KPI_POR_CLAVE.get(widget.clave_kpi)
        if kpi is None:
            errores.append(f"'{widget.clave_kpi}' no existe en KPI_REGISTRY")
            continue
        if widget.tipo_grafica not in kpi.graficas_permitidas:
            errores.append(
                f"'{widget.clave_kpi}' no admite la grafica '{widget.tipo_grafica}' "
                f"(admite: {', '.join(kpi.graficas_permitidas)})"
            )
        if widget.rango_relativo and widget.rango_relativo not in RANGOS_RELATIVOS:
            errores.append(f"'{widget.clave_kpi}': rango relativo desconocido '{widget.rango_relativo}'")
        if kpi.modo == "vivo":
            # Un KPI "vivo" es "ahora": no tiene periodo ni se compara.
            if widget.rango_relativo or widget.comparar_anterior or widget.comparar_desfase_dias:
                errores.append(f"'{widget.clave_kpi}' es un KPI en vivo: no lleva rango ni comparacion")
        elif not widget.rango_relativo:
            errores.append(f"'{widget.clave_kpi}' necesita un rango relativo (no es un KPI en vivo)")
        if (widget.comparar_anterior or widget.comparar_desfase_dias) and not widget.rango_relativo:
            errores.append(f"'{widget.clave_kpi}': comparar exige un rango relativo")
        if widget.comparar_anterior and widget.comparar_desfase_dias:
            errores.append(f"'{widget.clave_kpi}': comparar_anterior y comparar_desfase_dias son excluyentes")
    return errores


@dataclass
class AccionWidget:
    widget: WidgetPlantilla
    estado: str  # "crear" | "ya_existe"
    id_kpi_definition: int | None = None


@dataclass
class Plan:
    id_user: int | None = None
    id_tablero: int | None = None
    nombre_tablero: str = NOMBRE_TABLERO
    crear_tablero: bool = False
    acciones: list = field(default_factory=list)
    errores: list = field(default_factory=list)

    @property
    def por_crear(self):
        return [a for a in self.acciones if a.estado == "crear"]


def _user_data(user: User) -> dict:
    """Lo que el servicio espera de `user_data`: el MISMO payload que el login
    pone en el JWT (incluye si es el superusuario de arranque), no una copia."""
    return _user_payload(user)


def planear(session, username: str, nombre_tablero: str, plantilla=PLANTILLA) -> Plan:
    plan = Plan(nombre_tablero=nombre_tablero)
    user = session.scalars(select(User).where(User.username == username)).first()
    if user is None:
        plan.errores.append(f"el usuario '{username}' no existe en esta base")
        return plan
    plan.id_user = user.id_user
    user_data = _user_data(user)

    tablero = session.scalars(
        select(KpiDashboard).where(
            KpiDashboard.id_user == user.id_user,
            KpiDashboard.nombre == nombre_tablero,
            KpiDashboard.deletion_date.is_(None),
        )
    ).first()
    plan.id_tablero = tablero.id_kpi_dashboard if tablero else None
    plan.crear_tablero = tablero is None

    for widget in plantilla:
        kpi = session.scalars(
            select(KpiDefinition).where(KpiDefinition.clave == widget.clave_kpi, KpiDefinition.deletion_date.is_(None))
        ).first()
        if kpi is None:
            plan.errores.append(
                f"el KPI '{widget.clave_kpi}' no esta en kpi_definition (el backend lo siembra al arrancar)"
            )
            continue
        if not has_kpi_permission(session, user_data, kpi.id_kpi_definition):
            plan.errores.append(
                f"'{username}' no ve el KPI '{widget.clave_kpi}': corre primero "
                f"`python -m scripts.seed_kpi_permissions --perfil adser`"
            )
            continue
        ya_existe = tablero is not None and _widget_existente(session, tablero.id_kpi_dashboard, widget, kpi.id_kpi_definition)
        plan.acciones.append(AccionWidget(widget, "ya_existe" if ya_existe else "crear", kpi.id_kpi_definition))
    return plan


def _widget_existente(session, id_tablero: int, widget: WidgetPlantilla, id_kpi_definition: int) -> bool:
    """Hay un widget vivo, mismo tipo de grafica y con ESE KPI, en el tablero."""
    return session.scalars(
        select(KpiDashboardWidget.id_kpi_dashboard_widget)
        .join(
            KpiDashboardWidgetKpi,
            KpiDashboardWidgetKpi.id_kpi_dashboard_widget == KpiDashboardWidget.id_kpi_dashboard_widget,
        )
        .where(
            KpiDashboardWidget.id_kpi_dashboard == id_tablero,
            KpiDashboardWidget.deletion_date.is_(None),
            KpiDashboardWidget.tipo_grafica == widget.tipo_grafica,
            KpiDashboardWidgetKpi.id_kpi_definition == id_kpi_definition,
        )
    ).first() is not None


def aplicar(plan: Plan, username: str, hoy: date) -> None:
    """Escribe lo que `planear` decidio, por el mismo servicio que la API."""
    with transaction_context() as session:
        user = session.scalars(select(User).where(User.username == username)).first()
        user_data = _user_data(user)
    id_tablero = plan.id_tablero
    if plan.crear_tablero:
        creado = KpiDashboardService.create(
            {"id_user": plan.id_user, "nombre": plan.nombre_tablero}, user_id=plan.id_user,
        )
        id_tablero = creado["id_kpi_dashboard"]
        plan.id_tablero = id_tablero
    # Los widgets se ordenan a partir del ultimo que ya tenga el tablero.
    with transaction_context() as session:
        ultimo = max(
            session.scalars(
                select(KpiDashboardWidget.posicion_orden).where(
                    KpiDashboardWidget.id_kpi_dashboard == id_tablero,
                    KpiDashboardWidget.deletion_date.is_(None),
                )
            ).all() or [0]
        )
    orden = ultimo
    for accion in plan.acciones:
        if accion.estado != "crear":
            continue
        orden += 100
        try:
            KpiDashboardWidgetService.create_widget(
                user_data,
                id_tablero,
                {
                    "ids_kpi_definition": [accion.id_kpi_definition],
                    "tipo_grafica": accion.widget.tipo_grafica,
                    "parametros": parametros_del_widget(accion.widget, hoy),
                    "posicion_orden": orden,
                },
            )
        except AppError as error:
            raise SystemExit(f"ERROR al crear el widget de '{accion.widget.clave_kpi}': {error}") from error


_DESCRIPCION_ESTADO = {
    "crear": "CREAR",
    "ya_existe": "ya existe, sin cambios",
}


AVISO_TABLA = (
    "AVISO: la tabla 'Material prestado ahora' depende de incident.incident_date (la fecha del vale). "
    "NO correr en adser-prod hasta que Alan confirme, con una consulta de solo lectura, que esa fecha "
    "es confiable en lo migrado. Para crear los otros widgets sin ella: --sin-tabla."
)


def _es_vivo(widget: WidgetPlantilla) -> bool:
    kpi = KPI_POR_CLAVE.get(widget.clave_kpi)
    return bool(kpi and kpi.modo == "vivo")


def imprimir(plan: Plan, dry_run: bool, username: str) -> None:
    if plan.id_user is None:
        for error in plan.errores:
            print(f"  ERROR: {error}")
        return
    print(f"  Tablero '{plan.nombre_tablero}' de '{username}': {'CREAR' if plan.crear_tablero else 'ya existe, se reusa'}")
    for accion in plan.acciones:
        rango = accion.widget.rango_relativo or "en vivo"
        if accion.widget.comparar_desfase_dias:
            comparacion = f" + vs. hace {accion.widget.comparar_desfase_dias} dias"
        elif accion.widget.comparar_anterior:
            comparacion = " + vs. periodo anterior"
        else:
            comparacion = ""
        print(f"    {accion.widget.tipo_grafica:<7} {accion.widget.clave_kpi:<38} {rango}{comparacion:<26} {_DESCRIPCION_ESTADO[accion.estado]}")
    for error in plan.errores:
        print(f"  ERROR: {error}")
    if any(_es_vivo(accion.widget) for accion in plan.acciones):
        print(f"  {AVISO_TABLA}")
    if plan.errores:
        return  # con errores no se escribe nada: no se resume lo que "se crearia"
    verbo = "Se crearian" if dry_run else "Creados"
    print(f"{verbo}: {1 if plan.crear_tablero else 0} tablero(s) y {len(plan.por_crear)} widget(s).")


def main(argv=None, hoy: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra el tablero de KPIs de Adser para un usuario.")
    parser.add_argument("--usuario", default=USUARIO_POR_OMISION, help=f"nombre de usuario dueno del tablero (por omision '{USUARIO_POR_OMISION}')")
    parser.add_argument("--nombre", default=NOMBRE_TABLERO, help=f"nombre del tablero (por omision '{NOMBRE_TABLERO}')")
    parser.add_argument("--sin-tabla", action="store_true", help="omite la tabla 'Material prestado ahora' (ver el AVISO al inicio del archivo)")
    parser.add_argument("--dry-run", action="store_true", help="muestra lo que haria sin escribir nada")
    args = parser.parse_args(argv)
    hoy = hoy or date.today()
    plantilla = tuple(w for w in PLANTILLA if not (args.sin_tabla and _es_vivo(w)))

    errores = validar(plantilla)
    if errores:
        for error in errores:
            print(f"ERROR: {error}")
        print("No se escribio nada.")
        return 1

    print(f"Plantilla de tablero para '{args.usuario}'{' (dry-run: no se escribe nada)' if args.dry_run else ''}:")
    with transaction_context() as session:
        plan = planear(session, args.usuario, args.nombre, plantilla)
    if plan.errores:
        imprimir(plan, args.dry_run, args.usuario)
        print("No se escribio nada.")
        return 2 if plan.id_user is None else 1
    if not args.dry_run:
        aplicar(plan, args.usuario, hoy)
    imprimir(plan, args.dry_run, args.usuario)
    return 0


if __name__ == "__main__":
    sys.exit(main())
