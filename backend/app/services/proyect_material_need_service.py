"""La lista de necesidades de material de un proyecto, y lo que falta comprar.

Dos vistas de la misma tabla (`proyect_material_need`):

* **Por proyecto**: el supervisor declara lo que necesita su proyecto y ve, por
  renglon, cuanto hay en el almacen.
* **Por comprar**: quien compra ve las necesidades de TODOS los proyectos juntas,
  agrupadas por material y contra la existencia. Un mismo material pedido por tres
  proyectos es una sola compra, y es lo que esta vista deja ver.

La existencia no se reserva
---------------------------
"Hay N en el almacen" es la existencia del material hoy, sin descontar lo que
piden otros proyectos. Reservar existencia seria decidir quien se queda con que,
y eso es del almacen, no de esta lista. En "Por comprar" si se compara el TOTAL
pedido contra la existencia, que es la pregunta de quien compra: ¿alcanza lo que
hay para todos?

La existencia de un material es la suma de la de todos sus productos: el material
es lo que se pide ("disco de corte 4 1/2") y el producto es cada partida concreta
en el almacen.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.models import (
    InventoryStock, Material, Product, Proyect, ProyectMaterialNeed, Unit,
)
from app.models.session import transaction_context
from app.services.inventory_service import has_capability
from app.services.project_management_service import require_project_access
from app.utils.errors import AppError

# Un proyecto cerrado o negado ya no compra: sus necesidades abiertas son
# residuo, y contarlas inflaria lo que parece faltar.
PROYECTOS_QUE_YA_NO_COMPRAN = ("denied", "completed", "delivered")

PURCHASE_CAPABILITY = "purchase_planning"
NOTE_MAX = 300


# --- validacion de lo que llega ----------------------------------------------

def _actor(user_data: dict) -> int:
    try:
        id_user = int(user_data.get("id_user") or 0)
    except (TypeError, ValueError):
        id_user = 0
    if not id_user:
        raise AppError("errors.permission_denied", 403)
    return id_user


def _entero_positivo(valor, campo: str) -> int:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise AppError("errors.invalid_field", 400, {"field": campo})
    if numero <= 0:
        raise AppError("errors.invalid_field", 400, {"field": campo})
    return numero


def _fecha_o_nada(valor, campo: str) -> date | None:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError:
        raise AppError("errors.invalid_field", 400, {"field": campo})


def _nota(valor) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > NOTE_MAX:
        raise AppError("errors.field_too_long", 400, {
            "field": "note", "max_length": NOTE_MAX, "actual_length": len(texto)})
    return texto


# --- existencias -------------------------------------------------------------

def _existencias(db, ids_material) -> dict[int, int]:
    """Cuanto hay de cada material, sumando todos sus productos y todos sus sitios."""
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    filas = db.execute(
        select(Product.id_material, func.coalesce(func.sum(InventoryStock.quantity), 0))
        .join(InventoryStock, InventoryStock.id_product == Product.id_product)
        .where(Product.id_material.in_(ids), Product.deletion_date.is_(None))
        .group_by(Product.id_material)
    ).all()
    return {int(id_material): int(total or 0) for id_material, total in filas}


def _material(db, id_material) -> Material:
    material = db.scalars(
        select(Material).where(
            Material.id_material == id_material,
            Material.deletion_date.is_(None),
        )
    ).first()
    if material is None:
        raise AppError("errors.not_found", 404,
                       {"entity": "material", "field": "id_material"})
    return material


def _unidades(db, ids_material) -> dict[int, str | None]:
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    filas = db.execute(
        select(Material.id_material, Unit.unit_name)
        .outerjoin(Unit, Unit.id_unit == Material.id_unit)
        .where(Material.id_material.in_(ids))
    ).all()
    return {int(i): nombre for i, nombre in filas}


def _datos_de_materiales(db, ids_material) -> dict[int, dict]:
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    descripciones = dict(db.execute(
        select(Material.id_material, Material.material_description)
        .where(Material.id_material.in_(ids))
    ).all())
    unidades = _unidades(db, ids)
    return {
        i: {"id_material": i,
            "material_description": descripciones.get(i),
            "unit": unidades.get(i)}
        for i in ids
    }


def _renglon(need: ProyectMaterialNeed, materiales: dict, existencias: dict) -> dict:
    hay = existencias.get(int(need.id_material), 0)
    fila = need.serialize()
    fila.update({
        "material": materiales.get(int(need.id_material)),
        "in_stock": hay,
        # Informativo: contra la existencia de HOY, sin descontar a otros proyectos.
        "covered_by_stock": hay >= int(need.quantity),
    })
    return fila


def material_options() -> list[dict]:
    """Los materiales que se pueden pedir: solo id, nombre y unidad.

    Sin el permiso de lectura de `material` (modulo de inventario) a proposito,
    como `/user/options` o `/location/options`: el supervisor pide material
    para su proyecto sin administrar el catalogo, y sin esto el desplegable le
    llegaba vacio en cuanto se le quito ese permiso.
    """
    with transaction_context() as db:
        filas = db.execute(
            select(Material.id_material, Material.material_description, Unit.unit_name)
            .outerjoin(Unit, Unit.id_unit == Material.id_unit)
            .where(Material.deletion_date.is_(None))
            .order_by(Material.material_description)
        ).all()
        return [
            {"id_material": i, "material_description": descripcion, "unit": unidad}
            for i, descripcion, unidad in filas
        ]


# --- por proyecto ------------------------------------------------------------

def _necesidad(db, id_need, *, for_update=False) -> ProyectMaterialNeed:
    consulta = select(ProyectMaterialNeed).where(
        ProyectMaterialNeed.id_proyect_material_need == _entero_positivo(id_need, "id"),
        ProyectMaterialNeed.deletion_date.is_(None),
    )
    if for_update:
        consulta = consulta.with_for_update()
    need = db.scalars(consulta).first()
    if need is None:
        raise AppError("errors.resource_not_found", 404)
    return need


def list_needs(id_proyect, user_data: dict, *, incluir_canceladas: bool = False) -> dict:
    """Las necesidades de UN proyecto, solo si el actor puede ver ese proyecto."""
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    require_project_access(id_proyecto, user_data)
    with transaction_context() as db:
        consulta = select(ProyectMaterialNeed).where(
            ProyectMaterialNeed.id_proyect == id_proyecto,
            ProyectMaterialNeed.deletion_date.is_(None),
        ).order_by(ProyectMaterialNeed.id_proyect_material_need)
        if not incluir_canceladas:
            consulta = consulta.where(ProyectMaterialNeed.need_status == "open")
        necesidades = db.scalars(consulta).all()
        ids = {int(n.id_material) for n in necesidades}
        materiales = _datos_de_materiales(db, ids)
        existencias = _existencias(db, ids)
        return {
            "id_proyect": id_proyecto,
            "items": [_renglon(n, materiales, existencias) for n in necesidades],
        }


def create_need(id_proyect, payload: dict, user_data: dict) -> dict:
    actor = _actor(user_data)
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    require_project_access(id_proyecto, user_data)
    id_material = _entero_positivo(payload.get("id_material"), "id_material")
    cantidad = _entero_positivo(payload.get("quantity"), "quantity")
    necesaria_para = _fecha_o_nada(payload.get("needed_by"), "needed_by")
    nota = _nota(payload.get("note"))

    with transaction_context() as db:
        _material(db, id_material)

        # Dos renglones abiertos del mismo material en un proyecto son una lista
        # que miente: no se sabe cual vale. Se edita el que ya esta.
        existente = db.scalars(
            select(ProyectMaterialNeed).where(
                ProyectMaterialNeed.id_proyect == id_proyecto,
                ProyectMaterialNeed.id_material == id_material,
                ProyectMaterialNeed.need_status == "open",
                ProyectMaterialNeed.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if existente is not None:
            raise AppError("errors.need_duplicate_material", 409, {
                "id_proyect_material_need": existente.id_proyect_material_need,
                "id_material": id_material,
            })

        need = ProyectMaterialNeed(
            id_proyect=id_proyecto, id_material=id_material, quantity=cantidad,
            needed_by=necesaria_para, note=nota, need_status="open",
            created_by=actor,
        )
        db.add(need)
        db.flush()
        materiales = _datos_de_materiales(db, {id_material})
        return _renglon(need, materiales, _existencias(db, {id_material}))


def update_need(id_need, payload: dict, user_data: dict) -> dict:
    """Cantidad, fecha y nota de una necesidad ABIERTA."""
    _actor(user_data)
    with transaction_context() as db:
        need = _necesidad(db, id_need, for_update=True)
        require_project_access(need.id_proyect, user_data)
        if need.need_status != "open":
            raise AppError("errors.need_not_open", 409, {
                "id_proyect_material_need": need.id_proyect_material_need,
                "need_status": need.need_status})
        if "quantity" in payload:
            need.quantity = _entero_positivo(payload.get("quantity"), "quantity")
        if "needed_by" in payload:
            need.needed_by = _fecha_o_nada(payload.get("needed_by"), "needed_by")
        if "note" in payload:
            need.note = _nota(payload.get("note"))
        db.flush()
        materiales = _datos_de_materiales(db, {int(need.id_material)})
        return _renglon(need, materiales, _existencias(db, {int(need.id_material)}))


def cancel_need(id_need, user_data: dict) -> dict:
    """Ya no se necesita. No se borra: queda dicho que se pidio."""
    _actor(user_data)
    with transaction_context() as db:
        need = _necesidad(db, id_need, for_update=True)
        require_project_access(need.id_proyect, user_data)
        if need.need_status == "cancelled":
            return need.serialize()
        need.need_status = "cancelled"
        db.flush()
        return need.serialize()


# --- por comprar -------------------------------------------------------------

def _puede_ver_lo_que_falta(db, user_data: dict) -> bool:
    datos = user_data or {}
    if datos.get("is_superuser") or datos.get("is_bootstrap_admin"):
        return True
    return has_capability(db, user_data, PURCHASE_CAPABILITY)


def to_buy(user_data: dict, *, solo_faltantes: bool = True) -> dict:
    """Las necesidades de todos los proyectos, agrupadas por material.

    Por material: cuanto se pide en total, cuanto hay, y la diferencia. Y, para
    saber a quien le toca esa compra, que proyectos lo piden y para cuando.
    """
    _actor(user_data)
    with transaction_context() as db:
        if not _puede_ver_lo_que_falta(db, user_data):
            raise AppError("errors.permission_denied", 403,
                           {"capability": PURCHASE_CAPABILITY})

        filas = db.execute(
            select(ProyectMaterialNeed, Proyect.folio, Proyect.title,
                   Proyect.proyect_status)
            .join(Proyect, Proyect.id_proyect == ProyectMaterialNeed.id_proyect)
            .where(
                ProyectMaterialNeed.need_status == "open",
                ProyectMaterialNeed.deletion_date.is_(None),
                Proyect.deletion_date.is_(None),
                Proyect.proyect_status.notin_(PROYECTOS_QUE_YA_NO_COMPRAN),
            )
        ).all()

        ids = {int(n.id_material) for n, *_ in filas}
        materiales = _datos_de_materiales(db, ids)
        existencias = _existencias(db, ids)

        grupos: dict[int, dict] = {}
        for need, folio, titulo, estatus in filas:
            id_material = int(need.id_material)
            grupo = grupos.setdefault(id_material, {
                "material": materiales.get(id_material),
                "required": 0,
                "in_stock": existencias.get(id_material, 0),
                "needed_by": None,
                "projects": [],
            })
            grupo["required"] += int(need.quantity)
            if need.needed_by and (grupo["needed_by"] is None
                                   or need.needed_by < grupo["needed_by"]):
                grupo["needed_by"] = need.needed_by
            grupo["projects"].append({
                "id_proyect": need.id_proyect,
                "folio": folio,
                "title": titulo,
                "proyect_status": estatus,
                "quantity": int(need.quantity),
                "needed_by": need.needed_by.isoformat() if need.needed_by else None,
                "id_proyect_material_need": need.id_proyect_material_need,
            })

        items = []
        for grupo in grupos.values():
            grupo["missing"] = max(0, grupo["required"] - grupo["in_stock"])
            if solo_faltantes and grupo["missing"] == 0:
                continue
            fecha = grupo["needed_by"]
            grupo["needed_by"] = fecha.isoformat() if fecha else None
            items.append(grupo)

        # Lo que se necesita antes, primero; sin fecha al final; y a igual fecha,
        # lo que mas falta.
        items.sort(key=lambda g: (g["needed_by"] is None, g["needed_by"] or "",
                                  -g["missing"]))
        return {
            "items": items,
            "total": len(items),
            "only_missing": bool(solo_faltantes),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
