from sqlalchemy import select

from app.models import NmPermissionKpi
from app.models.entity_permission import EntityPermission
from app.models.kpi_definition import KpiDefinition
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError
from app.utils.scope import SCOPE_ALL


def exigir_eje_de_proyecto(id_permission, id_kpi_definition) -> None:
    """Rechaza darle a un rol un KPI que no esta acotado por proyecto si el rol no ve "Todos".

    Un KPI con `alcance_proyecto=False` (vales, incidencias, inventario, logistica...) calcula
    una sola vez para TODA la empresa y su snapshot no guarda `id_proyect`: quien lo ve, ve
    todo. Hasta ahora lo unico que lo impedia era `scripts/seed_kpi_permissions.py`; la
    pantalla `/kpi_permissions` y la API aceptaban cualquier asignacion.

    "Rol acotado" no es un dato guardado en ninguna parte: se toma del alcance de lectura que
    el propio rol tiene sobre `kpi_definition` (Gestor de roles y permisos). Un rol sin
    "Todos" (bit 4) -es decir con Propios, Mis grupos o sin acceso- esta acotado, y un KPI sin
    eje de proyecto no se le puede asignar. Quien ve "Todos" ya esta autorizado a ver toda la
    empresa, y es el caso de Administrator.

    LIMITACION (Q1, definicion pendiente de confirmar con el equipo): esta regla es una
    APROXIMACION, no la definicion de "rol acotado a proyecto".
    * No existe ese dato en ninguna tabla. En tiempo de ejecucion TODO usuario que no es
      superusuario queda acotado a su `id_proyect` (`InvoiceService.actor_project`), tenga el
      rol que tenga; "acotado a proyecto" y "alcance Propios/Mis grupos" son ejes distintos.
    * Un rol con "Todos" sobre `kpi_definition` sigue recibiendo KPIs sin eje de proyecto, y
      sus usuarios no superusuarios ven datos de toda la empresa con esos KPIs: ahi la barrera
      real es quien concede "Todos", no esta funcion.
    * Un rol sin fila de `kpi_definition` (sin alcance) tambien se rechaza, aunque todavia no
      pueda ver nada: es la opcion conservadora.
    * `scripts/seed_kpi_permissions.py` tiene su propia bandera manual `acotado_a_proyecto`;
      las dos reglas pueden discrepar.
    Si se define "rol acotado" de otra forma, este es el unico lugar que cambia.
    """
    from app.kpis.registry import ALCANCE_PROYECTO_POR_CLAVE

    if id_permission in (None, "") or id_kpi_definition in (None, ""):
        return
    with transaction_context() as db:
        kpi = db.get(KpiDefinition, int(id_kpi_definition))
        if kpi is None or ALCANCE_PROYECTO_POR_CLAVE.get(kpi.clave, True):
            return
        lectura = db.scalar(
            select(EntityPermission.scope_read).where(
                EntityPermission.id_permission == int(id_permission),
                EntityPermission.entity_name == "kpi_definition",
                EntityPermission.deletion_date.is_(None),
            )
        )
        if int(lectura or 0) & SCOPE_ALL:
            return
        clave = kpi.clave
    raise AppError(
        "errors.kpi_sin_eje_de_proyecto", 400,
        {"kpi": clave, "id_permission": int(id_permission),
         "reason": "El KPI no tiene alcance por proyecto y el rol no tiene alcance Todos sobre los KPIs."},
    )


class NmPermissionKpiService(CrudService):
    model = NmPermissionKpi
    primary_key = 'id_nm_permission_kpi'
    entity_name = 'nm_permission_kpi'

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        if (payload or {}).get('puede_ver', True):
            exigir_eje_de_proyecto((payload or {}).get('id_permission'), (payload or {}).get('id_kpi_definition'))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        # Se valida el resultado de la actualizacion, no solo el payload: cambiar solo el rol o
        # solo el KPI de una fila tambien puede crear la combinacion prohibida.
        actual = cls.get(item_id)
        final = {**actual, **(payload or {})}
        if final.get('puede_ver', True):
            exigir_eje_de_proyecto(final.get('id_permission'), final.get('id_kpi_definition'))
        return super().update(item_id, payload, user_id=user_id)
