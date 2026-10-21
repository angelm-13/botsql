"""La orden de compra, con la evidencia de que se compro.

El software no prueba que el dinero se gasto bien; hace que gastarlo mal sea dificil
y que se note. La orden recorre estos estados y cada paso lo da alguien distinto:

    borrador -> por autorizar -> autorizada -> comprada -> (recibida -> cerrada)
                     |               |
                  rechazada      cancelada (antes de comprar)

* **Compras** arma la orden -proveedor, renglones, costos- y la envia.
* **Quien autoriza** (capacidad `purchase_authorize`) la aprueba o la rechaza con un
  motivo. No puede autorizar la que el mismo escribio.
* **Comprar** es registrar el comprobante -factura o ticket- y como se pago. Sin el
  comprobante no se puede marcar comprada: el monto y el folio salen DEL
  comprobante, no de lo que teclee el comprador.
* Cada cambio de estado deja renglon en `purchase_event`, que solo se agrega.

Que protege cada cosa
---------------------
* El **mismo papel no justifica dos compras**: huella del archivo, folio del
  proveedor y UUID del CFDI son unicos en toda la base. Una orden SI puede surtir a
  varios proyectos (el reparto va en los renglones); lo que no puede pasar es contar
  el mismo comprobante en dos ordenes.
* El **proveedor tiene que ser uno dado de alta** (tipo proveedor): Compras no puede
  pagarle a quien nadie registro. Si el comprobante es un CFDI y el proveedor tiene
  RFC, el RFC del emisor tiene que ser ese.
* Un comprobante **fechado antes de que existiera la orden** es uno reciclado.
* Lo comprado no puede salir mas caro de lo autorizado mas la tolerancia de la
  politica: si sale, la orden VUELVE a autorizacion con el monto real.
* Lo que quede arriba del monto de gerencia lo compra quien autoriza, no Compras.

Los montos no estan en el codigo: viven en `purchase_policy` (una fila). Por omision
todo se autoriza y nadie compra por su cuenta.
"""
from __future__ import annotations

import json
import re
import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlalchemy import func, or_, select

from app.models import (
    CustomerSupplier, EntityPermission, Material, Proyect, ProyectMaterialNeed,
    PurchaseEvent, PurchaseOrder, PurchaseOrderLine, PurchasePolicy,
    PurchaseVoucher, User,
)
from app.models.purchase_order import PAYMENT_METHODS, VOUCHER_KINDS
from app.models.session import transaction_context
from app.services.cfdi_xml import parse_cfdi
from app.services.document_service import SecureDocumentStorage
from app.services import purchase_budget_service as presupuesto_de_compras
from app.services.proyect_material_need_service import (
    PROYECTOS_QUE_YA_NO_COMPRAN, _actor, _cantidad, _datos_de_materiales,
    _descripcion_valida, _entero_positivo, _fecha_o_nada, _texto, _unidad,
    needs_on_orders,
)
from app.utils.errors import AppError
from app.utils.tiempo import a_iso_utc

AUTHORIZE_CAPABILITY = "purchase_authorize"
RECEIVE_CAPABILITY = "purchase_receive"

CURRENCIES = ("MXN", "USD")
NOTE_MIN = 5
NOTE_MAX = 300
DESCRIPTION_MAX = 300
FOLIO_MAX = 60
REFERENCE_MAX = 80
MAX_AMOUNT = Decimal("100000000")
MAX_UNIT_COST = Decimal("10000000")
MAX_LINES = 200
# Un dia de holgura por el huso horario: el servidor cuenta en UTC y quien captura
# esta seis horas atras, asi que "hoy" para el puede ser "manana" para la base.
DATE_TOLERANCE = timedelta(days=1)
# Una compra registrada con meses de atraso no es un registro, es un archivo.
PURCHASE_DATE_MAX_AGE = timedelta(days=90)

SUBFOLDER = "purchase_vouchers"
# Los comprobantes que justifican el dinero: uno por orden.
EVIDENCE_KINDS = ("invoice", "receipt")
# En que estados de la orden se acepta cada tipo de comprobante, y en cuales se puede
# quitar. La factura y el ticket solo se suben YA autorizada la orden (se compra
# despues de autorizar). Y NO se pueden quitar mientras la orden espera una nueva
# autorizacion por exceder lo autorizado: quitar la factura cara para subir otra mas
# barata es justo lo que esa espera existe para evitar.
VOUCHER_STATES = {
    "quote": ("draft", "pending_authorization", "authorized", "rejected"),
    "invoice": ("authorized",),
    "receipt": ("authorized",),
    "payment_proof": ("authorized", "purchased", "partially_received", "received"),
}
# Tambien en `cancelled`: una orden cancelada seguia reteniendo su CFDI, que ya
# no se podia subir a una orden nueva (voucher_duplicate).
VOUCHER_REMOVABLE = {
    "quote": ("draft", "pending_authorization", "authorized", "rejected", "cancelled"),
    "invoice": ("authorized", "rejected", "cancelled"),
    "receipt": ("authorized", "rejected", "cancelled"),
    "payment_proof": ("authorized", "rejected", "cancelled"),
}
FILE_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}
EDITABLE_STATES = ("draft", "rejected")
CANCELLABLE_STATES = ("draft", "pending_authorization", "authorized", "rejected")
# Donde todavia falta (o puede faltar) material por recibir.
RECEIVABLE_STATES = ("purchased", "partially_received")
# Formas de pago que dejan una clave que contrastar con el estado de cuenta.
PAYMENT_NEEDS_REFERENCE = ("transfer", "check", "card")


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hoy() -> date:
    return _ahora().date()


def _sin_restriccion(user_data: dict) -> bool:
    datos = user_data or {}
    return bool(datos.get("is_superuser") or datos.get("is_bootstrap_admin"))


# --- validacion de lo que llega ----------------------------------------------

def _decimal(valor, campo: str, *, maximo: Decimal = MAX_AMOUNT, cuantos: str = "0.01",
             obligatorio: bool = True, permitir_cero: bool = False) -> Decimal | None:
    """Un monto, redondeado, positivo y con tope. El tope es contra el error de dedo."""
    if valor is None or str(valor).strip() == "":
        if obligatorio:
            raise AppError("errors.invalid_field", 400, {"field": campo})
        return None
    try:
        numero = Decimal(str(valor).strip().replace(",", ""))
    except InvalidOperation:
        raise AppError("errors.invalid_field", 400, {"field": campo})
    # `is_finite` va primero: comparar un NaN con algo revienta con otro error.
    if not numero.is_finite() or numero < 0 or (numero == 0 and not permitir_cero):
        raise AppError("errors.invalid_field", 400, {"field": campo})
    if numero > maximo:
        raise AppError("errors.invalid_field", 400, {"field": campo, "max": float(maximo)})
    return numero.quantize(Decimal(cuantos), rounding=ROUND_HALF_UP)


def _nota(valor, *, obligatoria: bool = False) -> str | None:
    texto = _texto(valor, "note", NOTE_MAX, obligatorio=obligatoria)
    if obligatoria and len(texto) < NOTE_MIN:
        raise AppError("errors.invalid_field", 400, {"field": "note"})
    return texto


def _json(datos) -> str | None:
    if not datos:
        return None
    return json.dumps(datos, default=str, ensure_ascii=False)


# --- la politica ---------------------------------------------------------------

def _politica(db) -> PurchasePolicy:
    """La fila unica de la politica. Si falta -una base sin migrar-, nace estricta."""
    fila = db.get(PurchasePolicy, 1)
    if fila is None:
        fila = PurchasePolicy(
            id_purchase_policy=1, authorize_above=Decimal("0"),
            manager_buys_above=None, overrun_percent=Decimal("10"))
        db.add(fila)
        db.flush()
    return fila


def _ficha_de_politica(fila: PurchasePolicy) -> dict:
    return {
        "authorize_above": float(fila.authorize_above),
        "manager_buys_above": (float(fila.manager_buys_above)
                               if fila.manager_buys_above is not None else None),
        "overrun_percent": float(fila.overrun_percent),
        "updated_by": fila.updated_by,
        "last_update_date": a_iso_utc(fila.last_update_date),
    }


def get_policy(user_data: dict) -> dict:
    _actor(user_data)
    with transaction_context() as db:
        return _ficha_de_politica(_politica(db))


def update_policy(payload: dict, user_data: dict) -> dict:
    """Fija desde que monto se autoriza y desde cual compra la gerencia.

    Quien compra no puede tocarla (la ruta pide `purchase_policy` y Compras solo la
    consulta): decidir desde que monto necesita permiso no es de quien lo necesita.
    """
    actor = _actor(user_data)
    with transaction_context() as db:
        fila = _politica(db)
        antes = _ficha_de_politica(fila)
        if "authorize_above" in payload:
            fila.authorize_above = _decimal(payload["authorize_above"], "authorize_above",
                                            permitir_cero=True)
        if "manager_buys_above" in payload:
            fila.manager_buys_above = _decimal(
                payload["manager_buys_above"], "manager_buys_above",
                obligatorio=False, permitir_cero=True)
        if "overrun_percent" in payload:
            porcentaje = _decimal(payload["overrun_percent"], "overrun_percent",
                                  maximo=Decimal("100"), permitir_cero=True)
            fila.overrun_percent = porcentaje
        # Comprar por encima de un monto sin pasar por autorizacion no tiene sentido:
        # el monto de gerencia no puede quedar por debajo del de autorizacion.
        if (fila.manager_buys_above is not None
                and fila.manager_buys_above < fila.authorize_above):
            raise AppError("errors.invalid_field", 400, {
                "field": "manager_buys_above", "min": float(fila.authorize_above)})
        fila.updated_by = actor
        db.flush()
        despues = _ficha_de_politica(fila)
        return {**despues, "previous": {k: antes[k] for k in (
            "authorize_above", "manager_buys_above", "overrun_percent")}}


# --- permisos ------------------------------------------------------------------

def _puede_autorizar(db, user_data: dict) -> bool:
    """Autorizar -y comprar lo que la politica reserva a gerencia- exige EDITAR la capacidad."""
    return _tiene_capacidad(db, user_data, AUTHORIZE_CAPABILITY)


def _puede_recibir(db, user_data: dict) -> bool:
    """Recibir lo comprado exige EDITAR la capacidad `purchase_receive`."""
    return _tiene_capacidad(db, user_data, RECEIVE_CAPABILITY)


def _tiene_capacidad(db, user_data: dict, capacidad: str) -> bool:
    from app.modules.plan import entidad_habilitada

    if not entidad_habilitada(capacidad):
        return False
    if _sin_restriccion(user_data):
        return True
    try:
        id_permission = int((user_data or {}).get("id_permission")
                            or (user_data or {}).get("permission_id") or 0)
    except (TypeError, ValueError):
        return False
    if not id_permission:
        return False
    fila = db.scalars(
        select(EntityPermission).where(
            EntityPermission.id_permission == id_permission,
            EntityPermission.entity_name == capacidad,
            EntityPermission.deletion_date.is_(None),
        ).limit(1)
    ).first()
    return bool(fila and int(fila.scope_update or 0) != 0)


def _exigir_autorizar(db, user_data: dict) -> None:
    if not _puede_autorizar(db, user_data):
        raise AppError("errors.permission_denied", 403, {"capability": AUTHORIZE_CAPABILITY})


def _exigir_recibir(db, user_data: dict) -> None:
    if not _puede_recibir(db, user_data):
        raise AppError("errors.permission_denied", 403, {"capability": RECEIVE_CAPABILITY})


# --- la bitacora ---------------------------------------------------------------

def _evento(db, orden: PurchaseOrder, tipo: str, actor: int, *, de: str | None = None,
            a: str | None = None, nota: str | None = None, detalle=None) -> None:
    """Un renglon en la bitacora. Solo se agrega: nada de aqui se edita ni se borra."""
    db.add(PurchaseEvent(
        id_purchase_order=orden.id_purchase_order, event_type=tipo, from_status=de,
        to_status=a, note=nota, detail=_json(detalle), created_by=actor))


def _cambiar_estado(db, orden: PurchaseOrder, nuevo: str, tipo: str, actor: int, *,
                    nota: str | None = None, detalle=None) -> None:
    anterior = orden.order_status
    orden.order_status = nuevo
    _evento(db, orden, tipo, actor, de=anterior, a=nuevo, nota=nota, detalle=detalle)


# --- lo que se carga -----------------------------------------------------------

def _orden(db, id_order, *, for_update: bool = False) -> PurchaseOrder:
    consulta = select(PurchaseOrder).where(
        PurchaseOrder.id_purchase_order == _entero_positivo(id_order, "id"),
        PurchaseOrder.deletion_date.is_(None),
    )
    if for_update:
        consulta = consulta.with_for_update()
    orden = db.scalars(consulta).first()
    if orden is None:
        raise AppError("errors.resource_not_found", 404)
    return orden


def _renglones(db, id_orden: int) -> list[PurchaseOrderLine]:
    return list(db.scalars(
        select(PurchaseOrderLine).where(
            PurchaseOrderLine.id_purchase_order == id_orden,
            PurchaseOrderLine.deletion_date.is_(None),
        ).order_by(PurchaseOrderLine.id_purchase_order_line)))


def _comprobantes(db, id_orden: int) -> list[PurchaseVoucher]:
    return list(db.scalars(
        select(PurchaseVoucher).where(
            PurchaseVoucher.id_purchase_order == id_orden,
            PurchaseVoucher.deletion_date.is_(None),
        ).order_by(PurchaseVoucher.id_purchase_voucher)))


def _total_de_renglones(renglones) -> Decimal | None:
    """Suma de cantidad por costo. Vacio si algun renglon no tiene costo todavia."""
    total = Decimal("0")
    for r in renglones:
        costo = r.unit_cost if hasattr(r, "unit_cost") else r["unit_cost"]
        cantidad = r.quantity if hasattr(r, "quantity") else r["quantity"]
        if costo is None:
            return None
        total += Decimal(cantidad) * Decimal(costo)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _proveedor(db, id_proveedor) -> CustomerSupplier:
    """Un proveedor DADO DE ALTA. Compras no puede pagarle a quien nadie registro."""
    proveedor = db.scalars(
        select(CustomerSupplier).where(
            CustomerSupplier.id_customer_supplier == _entero_positivo(
                id_proveedor, "id_customer_supplier"),
            CustomerSupplier.deletion_date.is_(None),
        )
    ).first()
    if proveedor is None:
        raise AppError("errors.resource_not_found", 404)
    if str(getattr(proveedor, "type", None) or "") != "supplier":
        raise AppError("errors.purchase_not_a_supplier", 409, {
            "id_customer_supplier": proveedor.id_customer_supplier})
    return proveedor


def _nombres(db, ids) -> dict[int, str]:
    ids = {int(i) for i in ids if i}
    if not ids:
        return {}
    filas = db.execute(
        select(User.id_user, User.full_name).where(User.id_user.in_(ids))).all()
    return {int(i): n for i, n in filas}


# --- los renglones ---------------------------------------------------------------

def _renglon_de_necesidad(db, dato: dict, tomadas: dict, excepto_orden) -> dict:
    id_necesidad = _entero_positivo(dato.get("id_proyect_material_need"),
                                    "id_proyect_material_need")
    necesidad = db.scalars(
        select(ProyectMaterialNeed).where(
            ProyectMaterialNeed.id_proyect_material_need == id_necesidad,
            ProyectMaterialNeed.deletion_date.is_(None),
        )
    ).first()
    if necesidad is None:
        raise AppError("errors.resource_not_found", 404)
    if necesidad.need_status != "open":
        raise AppError("errors.need_not_open", 409, {
            "id_proyect_material_need": id_necesidad, "need_status": necesidad.need_status})
    # Lo que nadie ha revisado, o se devolvio al supervisor, no se compra: seria
    # comprar algo que ni el almacen ni Compras han confirmado que se entiende.
    if necesidad.review_result not in ("buy", "linked"):
        raise AppError("errors.need_not_purchasable", 409, {
            "id_proyect_material_need": id_necesidad,
            "review_result": necesidad.review_result})
    proyecto = db.get(Proyect, necesidad.id_proyect)
    if (proyecto is None or proyecto.proyect_status in PROYECTOS_QUE_YA_NO_COMPRAN
            or proyecto.management_status == "cancelado"):
        raise AppError("errors.need_not_open", 409, {"id_proyect_material_need": id_necesidad})
    en_orden = tomadas.get(id_necesidad)
    if en_orden is not None and en_orden[0] != excepto_orden:
        raise AppError("errors.need_already_in_order", 409, {
            "id_proyect_material_need": id_necesidad,
            "id_purchase_order": en_orden[0], "order_folio": en_orden[1]})

    cantidad = (_cantidad(dato.get("quantity")) if str(dato.get("quantity") or "").strip()
                else int(necesidad.quantity))
    # No se compra mas de lo que el proyecto pidio: lo de mas es un renglon aparte,
    # sin necesidad, y esa diferencia se ve.
    if cantidad > int(necesidad.quantity):
        raise AppError("errors.invalid_field", 400, {
            "field": "quantity", "max": int(necesidad.quantity)})
    if necesidad.id_material is not None:
        material = _datos_de_materiales(db, {int(necesidad.id_material)}).get(
            int(necesidad.id_material)) or {}
        descripcion = material.get("material_description") or ""
        unidad = material.get("unit")
    else:
        descripcion, unidad = necesidad.description, necesidad.unit
    return {
        "id_proyect_material_need": id_necesidad,
        "id_proyect": necesidad.id_proyect,
        "id_material": necesidad.id_material,
        "description": descripcion,
        "unit": unidad,
        "quantity": cantidad,
        "unit_cost": _decimal(dato.get("unit_cost"), "unit_cost", maximo=MAX_UNIT_COST,
                              cuantos="0.0001", obligatorio=False),
    }


def _renglon_libre(db, dato: dict) -> dict:
    """Algo que Compras agrega por su cuenta, sin que lo pida un proyecto."""
    hay_material = str(dato.get("id_material") or "").strip() != ""
    id_material = _entero_positivo(dato.get("id_material"), "id_material") if hay_material else None
    unidad = None
    if id_material is not None:
        material = db.scalars(select(Material).where(
            Material.id_material == id_material, Material.deletion_date.is_(None))).first()
        if material is None:
            raise AppError("errors.resource_not_found", 404)
        info = _datos_de_materiales(db, {id_material}).get(id_material) or {}
        descripcion, unidad = info.get("material_description") or "", info.get("unit")
    else:
        descripcion = _descripcion_valida(_texto(
            dato.get("description"), "description", 200, obligatorio=True))
        unidad = _unidad(dato.get("unit"))
    id_proyecto = None
    if str(dato.get("id_proyect") or "").strip() != "":
        id_proyecto = _entero_positivo(dato.get("id_proyect"), "id_proyect")
        if db.get(Proyect, id_proyecto) is None:
            raise AppError("errors.resource_not_found", 404)
    return {
        "id_proyect_material_need": None,
        "id_proyect": id_proyecto,
        "id_material": id_material,
        "description": descripcion,
        "unit": unidad,
        "quantity": _cantidad(dato.get("quantity")),
        "unit_cost": _decimal(dato.get("unit_cost"), "unit_cost", maximo=MAX_UNIT_COST,
                              cuantos="0.0001", obligatorio=False),
    }


def _preparar_renglones(db, datos, *, excepto_orden: int | None = None) -> list[dict]:
    if not isinstance(datos, list):
        raise AppError("errors.invalid_field", 400, {"field": "lines"})
    if len(datos) > MAX_LINES:
        raise AppError("errors.invalid_field", 400, {"field": "lines", "max": MAX_LINES})
    ids = [d.get("id_proyect_material_need") for d in datos if isinstance(d, dict)
           and str(d.get("id_proyect_material_need") or "").strip() != ""]
    vistas = set()
    for i in ids:
        if str(i) in vistas:
            raise AppError("errors.order_duplicate_line", 409, {
                "id_proyect_material_need": i})
        vistas.add(str(i))
    numericas = sorted({int(i) for i in ids if str(i).isdigit()})
    if numericas:
        # Dos ordenes creadas a la vez por la misma necesidad leian "nadie la
        # tiene" las dos. Se bloquean las filas (en orden, para no abrazarse) y
        # LUEGO se mira quien la tiene: la segunda espera y ya ve a la primera.
        db.execute(select(ProyectMaterialNeed.id_proyect_material_need).where(
            ProyectMaterialNeed.id_proyect_material_need.in_(numericas)
        ).order_by(ProyectMaterialNeed.id_proyect_material_need).with_for_update())
    tomadas = needs_on_orders(db, numericas, excepto_orden=excepto_orden)
    resultado = []
    for dato in datos:
        if not isinstance(dato, dict):
            raise AppError("errors.invalid_field", 400, {"field": "lines"})
        if str(dato.get("id_proyect_material_need") or "").strip() != "":
            resultado.append(_renglon_de_necesidad(db, dato, tomadas, excepto_orden))
        else:
            resultado.append(_renglon_libre(db, dato))
    return resultado


def _guardar_renglones(db, orden: PurchaseOrder, renglones: list[dict], actor: int) -> None:
    for r in renglones:
        db.add(PurchaseOrderLine(id_purchase_order=orden.id_purchase_order,
                                 created_by=actor, **r))
    db.flush()


def _retirar_renglones(db, orden: PurchaseOrder) -> None:
    ahora = _ahora()
    for r in _renglones(db, orden.id_purchase_order):
        r.deletion_date = ahora
    db.flush()


# --- la ficha ------------------------------------------------------------------

def _puede_escribir_ordenes(db, user_data: dict) -> bool:
    """Si el actor puede actualizar ordenes, que es lo que pide cada accion en la ruta."""
    if _sin_restriccion(user_data):
        return True
    try:
        id_permission = int((user_data or {}).get("id_permission")
                            or (user_data or {}).get("permission_id") or 0)
    except (TypeError, ValueError):
        return False
    if not id_permission:
        return False
    fila = db.scalars(
        select(EntityPermission).where(
            EntityPermission.id_permission == id_permission,
            EntityPermission.entity_name == "purchase_order",
            EntityPermission.deletion_date.is_(None),
        ).limit(1)
    ).first()
    return bool(fila and int(fila.scope_update or 0) != 0)


def _acciones(db, orden: PurchaseOrder, renglones, comprobantes, user_data: dict,
              actor: int) -> dict:
    """Lo que ESTE actor puede hacer con la orden ahora, para pintar solo esos botones.

    Es ayuda para la pantalla, no seguridad: cada accion se vuelve a comprobar en su
    servicio. Quien solo puede VER la orden -el almacen- no recibe ningun boton.
    """
    estado = orden.order_status
    escribe = _puede_escribir_ordenes(db, user_data)
    autoriza = escribe and _puede_autorizar(db, user_data)
    con_evidencia = [v for v in comprobantes if v.kind in EVIDENCE_KINDS]
    if orden.requires_manager_purchase:
        puede_comprar = autoriza
    else:
        puede_comprar = orden.authorized_by is None or orden.authorized_by != actor
    return {
        "edit": escribe and estado in EDITABLE_STATES,
        "submit": escribe and estado in EDITABLE_STATES and bool(renglones),
        "authorize": estado == "pending_authorization" and autoriza
        and orden.created_by != actor,
        "reject": estado == "pending_authorization" and autoriza,
        "attach_voucher": escribe and estado in (
            "draft", "pending_authorization", "authorized", "rejected", "purchased",
            "partially_received", "received"),
        "purchase": escribe and estado == "authorized" and puede_comprar
        and bool(con_evidencia),
        "cancel": escribe and estado in CANCELLABLE_STATES,
        # Recibir lo comprado es del almacen, que solo consulta las ordenes: lo
        # decide la capacidad `purchase_receive`, no el permiso de escribir. Quien
        # puede recibir lo manda el Gestor: no hay regla por persona.
        "receive": estado in RECEIVABLE_STATES and _puede_recibir(db, user_data),
        # Cuales comprobantes se pueden quitar ahora (y solo antes de comprar).
        "removable_vouchers": [
            v.id_purchase_voucher for v in comprobantes
            if escribe and estado in VOUCHER_REMOVABLE[v.kind]],
    }


def _ficha(db, orden: PurchaseOrder, user_data: dict, *, detalle: bool = True) -> dict:
    actor = _actor(user_data)
    renglones = _renglones(db, orden.id_purchase_order)
    comprobantes = _comprobantes(db, orden.id_purchase_order)
    proveedor = db.get(CustomerSupplier, orden.id_customer_supplier)
    ficha = orden.serialize()

    ids_proyecto = {int(r.id_proyect) for r in renglones if r.id_proyect}
    proyectos = {}
    if ids_proyecto:
        proyectos = {
            int(i): {"id_proyect": int(i), "folio": f, "title": t}
            for i, f, t in db.execute(
                select(Proyect.id_proyect, Proyect.folio, Proyect.title)
                .where(Proyect.id_proyect.in_(ids_proyecto)))
        }
    lineas = []
    for r in renglones:
        fila = r.serialize()
        fila["project"] = proyectos.get(int(r.id_proyect)) if r.id_proyect else None
        fila["from_need"] = r.id_proyect_material_need is not None
        fila["line_total"] = (float((Decimal(r.quantity) * Decimal(r.unit_cost))
                                    .quantize(Decimal("0.01")))
                              if r.unit_cost is not None else None)
        lineas.append(fila)
    ficha.update({
        "supplier": {
            "id_customer_supplier": orden.id_customer_supplier,
            "name": proveedor.name if proveedor else None,
            "tax_id": proveedor.tax_id if proveedor else None,
        },
        "lines": lineas,
        "lines_total": (float(_total_de_renglones(renglones))
                        if renglones and _total_de_renglones(renglones) is not None else None),
        "projects": sorted(proyectos.values(), key=lambda p: p["id_proyect"]),
        "budget": (json.loads(orden.budget_detail) if orden.budget_detail else []),
        "vouchers": [v.serialize() for v in comprobantes],
        "actions": _acciones(db, orden, renglones, comprobantes, user_data, actor),
    })
    if detalle:
        eventos = list(db.scalars(
            select(PurchaseEvent).where(
                PurchaseEvent.id_purchase_order == orden.id_purchase_order,
            ).order_by(PurchaseEvent.id_purchase_event)))
        nombres = _nombres(db, {e.created_by for e in eventos} | {
            orden.created_by, orden.authorized_by, orden.purchased_by}
            | {v.created_by for v in comprobantes})
        ficha["events"] = [
            {**e.serialize(), "created_by_name": nombres.get(int(e.created_by))}
            for e in eventos]
        ficha["created_by_name"] = nombres.get(int(orden.created_by))
        ficha["authorized_by_name"] = nombres.get(int(orden.authorized_by)) if orden.authorized_by else None
        ficha["purchased_by_name"] = nombres.get(int(orden.purchased_by)) if orden.purchased_by else None
        for v in ficha["vouchers"]:
            v["created_by_name"] = nombres.get(int(v["created_by"]))
    return ficha


# --- consultar ---------------------------------------------------------------------

def list_orders(user_data: dict, *, status=None, id_supplier=None, q=None,
                limit: int = 100, offset: int = 0) -> dict:
    _actor(user_data)
    limite = max(1, min(int(limit or 100), 200))
    desde = max(0, int(offset or 0))
    with transaction_context() as db:
        consulta = (
            select(PurchaseOrder, CustomerSupplier.name)
            .join(CustomerSupplier,
                  CustomerSupplier.id_customer_supplier == PurchaseOrder.id_customer_supplier)
            .where(PurchaseOrder.deletion_date.is_(None))
        )
        if status:
            estados = [s for s in str(status).split(",") if s in (
                "draft", "pending_authorization", "authorized", "rejected", "purchased",
                "partially_received", "received", "closed", "cancelled")]
            if estados:
                consulta = consulta.where(PurchaseOrder.order_status.in_(estados))
        if id_supplier:
            consulta = consulta.where(
                PurchaseOrder.id_customer_supplier == _entero_positivo(id_supplier, "supplier"))
        texto = " ".join(str(q or "").split())
        if texto:
            patron = "%" + texto.lower() + "%"
            consulta = consulta.where(or_(
                func.lower(PurchaseOrder.folio).like(patron),
                func.lower(CustomerSupplier.name).like(patron),
                func.lower(func.coalesce(PurchaseOrder.description, "")).like(patron),
                func.lower(func.coalesce(PurchaseOrder.purchase_folio, "")).like(patron),
            ))
        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = db.execute(
            consulta.order_by(PurchaseOrder.id_purchase_order.desc())
            .limit(limite).offset(desde)).all()

        ids = [o.id_purchase_order for o, _ in filas]
        conteos = {}
        if ids:
            conteos = {
                int(i): (int(n), int(p)) for i, n, p in db.execute(
                    select(PurchaseOrderLine.id_purchase_order,
                           func.count(PurchaseOrderLine.id_purchase_order_line),
                           func.count(func.distinct(PurchaseOrderLine.id_proyect)))
                    .where(PurchaseOrderLine.id_purchase_order.in_(ids),
                           PurchaseOrderLine.deletion_date.is_(None))
                    .group_by(PurchaseOrderLine.id_purchase_order))
            }
        nombres = _nombres(db, {o.created_by for o, _ in filas})
        items = []
        for orden, proveedor in filas:
            n, p = conteos.get(int(orden.id_purchase_order), (0, 0))
            fila = orden.serialize()
            fila.update({
                "supplier_name": proveedor, "lines_count": n, "projects_count": p,
                "created_by_name": nombres.get(int(orden.created_by)),
            })
            items.append(fila)
        # Cuantas hay en cada estado, sin los filtros de la lista: es el resumen
        # que se ve arriba de la pantalla (por autorizar, por comprar, por recibir).
        por_estado = {
            str(estado): int(n) for estado, n in db.execute(
                select(PurchaseOrder.order_status, func.count())
                .where(PurchaseOrder.deletion_date.is_(None))
                .group_by(PurchaseOrder.order_status)).all()
        }
        return {"items": items, "total": int(total or 0), "limit": limite, "offset": desde,
                "by_status": por_estado}


def get_order(id_order, user_data: dict) -> dict:
    with transaction_context() as db:
        return _ficha(db, _orden(db, id_order), user_data)


def supplier_options(user_data: dict, q=None) -> list[dict]:
    """Los proveedores dados de alta, para elegir uno. Sin permiso de CRM a proposito:
    Compras escoge de la lista, no la edita -dar de alta a quien se le va a pagar es de
    quien administra Clientes y proveedores."""
    _actor(user_data)
    with transaction_context() as db:
        consulta = select(CustomerSupplier.id_customer_supplier, CustomerSupplier.name,
                          CustomerSupplier.tax_id).where(
            CustomerSupplier.deletion_date.is_(None),
            CustomerSupplier.type == "supplier",
        ).order_by(CustomerSupplier.name).limit(200)
        texto = " ".join(str(q or "").split())
        if texto:
            consulta = consulta.where(
                func.lower(CustomerSupplier.name).like("%" + texto.lower() + "%"))
        return [{"id_customer_supplier": int(i), "name": n, "tax_id": t}
                for i, n, t in db.execute(consulta)]


# --- armar la orden ------------------------------------------------------------

def _moneda(valor) -> str:
    moneda = str(valor or "MXN").strip().upper()
    if moneda not in CURRENCIES:
        raise AppError("errors.invalid_field", 400, {
            "field": "currency", "allowed": list(CURRENCIES)})
    return moneda


def create_order(payload: dict, user_data: dict) -> dict:
    actor = _actor(user_data)
    descripcion = _texto(payload.get("description"), "description", DESCRIPTION_MAX)
    esperada = _fecha_o_nada(payload.get("expected_date"), "expected_date")
    moneda = _moneda(payload.get("currency"))
    with transaction_context() as db:
        proveedor = _proveedor(db, payload.get("id_customer_supplier"))
        renglones = _preparar_renglones(db, payload.get("lines") or [])
        # El folio se conoce hasta tener id: se asigna tras el primer flush, con un
        # marcador unico mientras tanto.
        orden = PurchaseOrder(
            folio="OC-NUEVA-" + uuid.uuid4().hex[:12],
            id_customer_supplier=proveedor.id_customer_supplier,
            order_status="draft", description=descripcion, expected_date=esperada,
            currency=moneda, created_by=actor)
        db.add(orden)
        db.flush()
        orden.folio = "OC-%d-%05d" % (_hoy().year, orden.id_purchase_order)
        _guardar_renglones(db, orden, renglones, actor)
        orden.quoted_total = _total_de_renglones(renglones) if renglones else None
        _evento(db, orden, "created", actor, a="draft", detalle={
            "supplier": proveedor.name, "lines": len(renglones)})
        db.flush()
        return _ficha(db, orden, user_data)


def update_order(id_order, payload: dict, user_data: dict) -> dict:
    """Edita una orden que todavia no se envia (o que se rechazo y se corrige)."""
    actor = _actor(user_data)
    with transaction_context() as db:
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status not in EDITABLE_STATES:
            raise AppError("errors.order_not_editable", 409, {
                "order_status": orden.order_status})
        cambios = {}
        if "description" in payload:
            nueva = _texto(payload.get("description"), "description", DESCRIPTION_MAX)
            if nueva != orden.description:
                cambios["description"] = [orden.description, nueva]
                orden.description = nueva
        if "expected_date" in payload:
            nueva = _fecha_o_nada(payload.get("expected_date"), "expected_date")
            if nueva != orden.expected_date:
                cambios["expected_date"] = [orden.expected_date, nueva]
                orden.expected_date = nueva
        if "currency" in payload:
            nueva = _moneda(payload.get("currency"))
            if nueva != orden.currency:
                cambios["currency"] = [orden.currency, nueva]
                orden.currency = nueva
        if "id_customer_supplier" in payload:
            proveedor = _proveedor(db, payload.get("id_customer_supplier"))
            if proveedor.id_customer_supplier != orden.id_customer_supplier:
                cambios["supplier"] = [orden.id_customer_supplier, proveedor.id_customer_supplier]
                orden.id_customer_supplier = proveedor.id_customer_supplier
        if "lines" in payload:
            antes = _total_de_renglones(_renglones(db, orden.id_purchase_order))
            renglones = _preparar_renglones(
                db, payload.get("lines"), excepto_orden=orden.id_purchase_order)
            _retirar_renglones(db, orden)
            _guardar_renglones(db, orden, renglones, actor)
            orden.quoted_total = _total_de_renglones(renglones) if renglones else None
            cambios["lines"] = {"count": len(renglones), "total": [antes, orden.quoted_total]}
        if orden.order_status == "rejected" and cambios:
            _cambiar_estado(db, orden, "draft", "reopened", actor, detalle=cambios)
        elif cambios:
            _evento(db, orden, "updated", actor, detalle=cambios)
        db.flush()
        return _ficha(db, orden, user_data)


def submit_order(id_order, user_data: dict) -> dict:
    """Manda la orden a autorizacion. Si la politica no la exige, queda autorizada."""
    actor = _actor(user_data)
    with transaction_context() as db:
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status not in EDITABLE_STATES:
            raise AppError("errors.order_not_editable", 409, {
                "order_status": orden.order_status})
        renglones = _renglones(db, orden.id_purchase_order)
        if not renglones:
            raise AppError("errors.order_without_lines", 409)
        total = _total_de_renglones(renglones)
        if total is None or total <= 0:
            # Autorizar sin saber cuanto cuesta es firmar en blanco.
            raise AppError("errors.order_without_costs", 409)
        _proveedor(db, orden.id_customer_supplier)

        politica = _politica(db)
        requiere = total > politica.authorize_above
        evaluacion = presupuesto_de_compras.evaluar_orden(db, orden, renglones)
        se_pasa = presupuesto_de_compras.excede(evaluacion)
        # Pasarse del presupuesto de un proyecto exige autorizacion aunque el monto sea chico.
        requiere = requiere or se_pasa
        orden.exceeds_budget = se_pasa
        orden.budget_detail = json.dumps(evaluacion) if evaluacion else None
        gerente = (politica.manager_buys_above is not None
                   and total > politica.manager_buys_above)
        orden.quoted_total = total
        orden.requires_authorization = requiere
        orden.requires_manager_purchase = gerente
        orden.authorized_by = None
        orden.authorized_date = None
        orden.authorization_note = None
        orden.authorized_total = None
        detalle = {"total": total, "authorize_above": politica.authorize_above,
                   "manager_buys_above": politica.manager_buys_above,
                   "exceeds_budget": se_pasa}
        anterior = orden.order_status
        if requiere:
            _cambiar_estado(db, orden, "pending_authorization", "submitted", actor,
                            detalle=detalle)
        else:
            # La politica no la exige: queda autorizada sin autorizador, y asi consta.
            orden.authorized_total = total
            _cambiar_estado(db, orden, "authorized", "auto_authorized", actor,
                            nota="Monto por debajo del limite de autorizacion",
                            detalle=detalle)
        if anterior == "rejected":
            _evento(db, orden, "resubmitted", actor, de="rejected",
                    a=orden.order_status)
        db.flush()
        return _ficha(db, orden, user_data)


def authorize_order(id_order, payload: dict, user_data: dict) -> dict:
    actor = _actor(user_data)
    nota = _nota(payload.get("note"))
    with transaction_context() as db:
        _exigir_autorizar(db, user_data)
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status != "pending_authorization":
            raise AppError("errors.order_not_pending", 409, {"order_status": orden.order_status})
        # Quien pide el dinero no se lo autoriza. Vale tambien para el administrador.
        if int(orden.created_by) == actor:
            raise AppError("errors.purchase_same_person", 403, {"action": "authorize"})
        # Otras ordenes pudieron comprometer el presupuesto desde que esta se envio.
        evaluacion = presupuesto_de_compras.evaluar_orden(
            db, orden, _renglones(db, orden.id_purchase_order), al_autorizar=True)
        orden.exceeds_budget = presupuesto_de_compras.excede(evaluacion)
        orden.budget_detail = json.dumps(evaluacion) if evaluacion else None
        if orden.exceeds_budget and not nota:
            # Autorizar por encima del presupuesto deja el motivo por escrito.
            raise AppError("errors.budget_note_required", 400, {
                "detail": presupuesto_de_compras.resumen_del_exceso(evaluacion)})
        orden.authorized_by = actor
        orden.authorized_date = _ahora()
        orden.authorization_note = nota
        orden.authorized_total = orden.quoted_total
        _cambiar_estado(db, orden, "authorized", "authorized", actor, nota=nota,
                        detalle={"authorized_total": orden.authorized_total})
        db.flush()
        return _ficha(db, orden, user_data)


def reject_order(id_order, payload: dict, user_data: dict) -> dict:
    actor = _actor(user_data)
    nota = _nota(payload.get("note"), obligatoria=True)
    with transaction_context() as db:
        _exigir_autorizar(db, user_data)
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status != "pending_authorization":
            raise AppError("errors.order_not_pending", 409, {"order_status": orden.order_status})
        orden.authorized_by = None
        orden.authorized_date = None
        orden.authorized_total = None
        orden.authorization_note = nota
        _cambiar_estado(db, orden, "rejected", "rejected", actor, nota=nota)
        db.flush()
        return _ficha(db, orden, user_data)


def cancel_order(id_order, payload: dict, user_data: dict) -> dict:
    """Cancelar libera las necesidades que la orden sostenia. Se pide un motivo."""
    actor = _actor(user_data)
    nota = _nota(payload.get("note"), obligatoria=True)
    with transaction_context() as db:
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status not in CANCELLABLE_STATES:
            # Ya se compro: deshacerlo es una devolucion o una nota de credito, no
            # borrar una orden.
            raise AppError("errors.order_not_cancellable", 409, {
                "order_status": orden.order_status})
        _cambiar_estado(db, orden, "cancelled", "cancelled", actor, nota=nota)
        db.flush()
        return _ficha(db, orden, user_data)


# --- los comprobantes -----------------------------------------------------------

def _inspeccionar_archivo(storage: SecureDocumentStorage, raw: bytes, nombre: str):
    """(extension, mime, datos del CFDI o None). El XML se lee; lo demas se valida por forma."""
    extension = str(nombre or "").rsplit(".", 1)[-1].lower() if "." in str(nombre or "") else ""
    if extension == "xml":
        if not raw or len(raw) > storage.max_bytes:
            raise AppError("documents.invalid_file_size", 400, {"max_bytes": storage.max_bytes})
        try:
            return "xml", "application/xml", parse_cfdi(raw)
        except ValueError as exc:
            raise AppError("errors.voucher_invalid_cfdi", 400, {"reason": str(exc)})
    extension, mime = storage.validate(raw, nombre, allowed_types=FILE_TYPES)
    return extension, mime, None


def _duplicado(db, *, sha256: str, id_proveedor: int, folio: str | None,
               uuid_cfdi: str | None, tipo: str):
    """Otro comprobante vivo que ya justifica una compra con ese mismo papel, o None."""
    llaves = [("file", PurchaseVoucher.sha256 == sha256)]
    if uuid_cfdi:
        llaves.append(("cfdi", PurchaseVoucher.cfdi_uuid == uuid_cfdi))
    if folio and tipo in EVIDENCE_KINDS:
        llaves.append(("folio", (PurchaseVoucher.id_customer_supplier == id_proveedor)
                       & (func.upper(PurchaseVoucher.folio) == folio.upper())
                       & PurchaseVoucher.kind.in_(EVIDENCE_KINDS)))
    for clave, condicion in llaves:
        fila = db.execute(
            select(PurchaseVoucher, PurchaseOrder.folio, PurchaseOrder.id_purchase_order)
            .join(PurchaseOrder,
                  PurchaseOrder.id_purchase_order == PurchaseVoucher.id_purchase_order)
            .where(condicion, PurchaseVoucher.deletion_date.is_(None)).limit(1)
        ).first()
        if fila is not None:
            return clave, fila[1], fila[2]
    return None


def add_voucher(id_order, campos: dict, raw: bytes, nombre: str, user_data: dict,
                storage: SecureDocumentStorage) -> dict:
    """Sube un comprobante a la orden.

    El archivo se compara por su huella; si es un CFDI se lee y lo que dice el propio
    archivo -UUID, emisor, monto, fecha- manda sobre lo que se teclee.
    """
    actor = _actor(user_data)
    tipo = str(campos.get("kind") or "").strip().lower()
    if tipo not in VOUCHER_KINDS:
        raise AppError("errors.invalid_field", 400, {"field": "kind", "allowed": list(VOUCHER_KINDS)})
    extension, mime, cfdi = _inspeccionar_archivo(storage, raw, nombre)
    if cfdi is not None and tipo not in EVIDENCE_KINDS:
        # Un XML de CFDI es la factura. Una cotizacion o un comprobante de pago son
        # PDF o foto.
        raise AppError("errors.voucher_xml_only_for_invoice", 400)
    huella = hashlib.sha256(raw).hexdigest()

    with transaction_context() as db:
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status not in VOUCHER_STATES[tipo]:
            raise AppError("errors.voucher_not_allowed_now", 409, {
                "kind": tipo, "order_status": orden.order_status})
        if tipo in EVIDENCE_KINDS and any(
                v.kind in EVIDENCE_KINDS for v in _comprobantes(db, orden.id_purchase_order)):
            # Un comprobante por orden: la compra tiene UNA factura o UN ticket. Si el
            # que se subio esta mal, se quita (queda en la bitacora) y se sube el bueno.
            raise AppError("errors.voucher_one_per_order", 409)
        proveedor = db.get(CustomerSupplier, orden.id_customer_supplier)

        folio = _texto(campos.get("folio"), "folio", FOLIO_MAX)
        monto = _decimal(campos.get("amount"), "amount", obligatorio=False)
        emitido = _fecha_o_nada(campos.get("issue_date"), "issue_date")
        uuid_cfdi = rfc_emisor = None
        if cfdi is not None:
            uuid_cfdi = cfdi["uuid"]
            rfc_emisor = (cfdi.get("rfc_emisor") or "").strip().upper() or None
            if str(cfdi.get("tipo_de_comprobante") or "I").upper() != "I":
                raise AppError("errors.voucher_not_an_invoice", 400, {
                    "type": cfdi.get("tipo_de_comprobante")})
            if str(cfdi.get("currency") or "MXN").upper() != orden.currency:
                raise AppError("errors.voucher_currency_mismatch", 409, {
                    "order_currency": orden.currency, "voucher_currency": cfdi.get("currency")})
            total = Decimal(cfdi["total"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if monto is not None and monto != total:
                raise AppError("errors.voucher_amount_mismatch", 409, {
                    "typed": float(monto), "in_file": float(total)})
            monto = total
            folio = ((cfdi.get("serie") or "") + (cfdi.get("folio") or "")) or uuid_cfdi
            if cfdi.get("fecha"):
                emitido = _fecha_o_nada(cfdi["fecha"], "issue_date")
            tax_id = (proveedor.tax_id or "").strip().upper() if proveedor else ""
            if tax_id and rfc_emisor and tax_id != rfc_emisor:
                raise AppError("errors.voucher_supplier_mismatch", 409, {
                    "supplier_tax_id": tax_id, "voucher_tax_id": rfc_emisor})

        if tipo in EVIDENCE_KINDS:
            if not folio or monto is None or emitido is None:
                # Sin folio, monto y fecha no hay nada que contrastar.
                raise AppError("errors.voucher_incomplete", 400, {
                    "missing": [c for c, v in (("folio", folio), ("amount", monto),
                                               ("issue_date", emitido)) if not v]})
            # Fechado antes de que existiera la orden: es un papel reciclado.
            if emitido < orden.creation_date.date() - DATE_TOLERANCE:
                raise AppError("errors.voucher_predates_order", 409, {
                    "issue_date": emitido.isoformat(),
                    "order_date": orden.creation_date.date().isoformat()})
            if emitido > _hoy() + DATE_TOLERANCE:
                raise AppError("errors.invalid_field", 400, {"field": "issue_date"})

        previo = _duplicado(db, sha256=huella, id_proveedor=orden.id_customer_supplier,
                            folio=folio, uuid_cfdi=uuid_cfdi, tipo=tipo)
        if previo is not None:
            clave, folio_orden, id_orden_previa = previo
            raise AppError("errors.voucher_duplicate", 409, {
                "matched_on": clave, "order_folio": folio_orden,
                "id_purchase_order": id_orden_previa})

        voucher = PurchaseVoucher(
            id_purchase_order=orden.id_purchase_order,
            id_customer_supplier=orden.id_customer_supplier, kind=tipo, folio=folio,
            amount=monto, issue_date=emitido,
            original_filename=str(nombre or "")[:255], extension=extension,
            mime_type=mime, file_size=len(raw), sha256=huella, file_path="",
            cfdi_uuid=uuid_cfdi, rfc_emisor=rfc_emisor, created_by=actor)
        db.add(voucher)
        db.flush()
        voucher.file_path = storage.write(
            raw, orden.id_purchase_order, voucher.id_purchase_voucher, 1, extension,
            subfolder=SUBFOLDER)
        _evento(db, orden, "voucher_added", actor, nota=None, detalle={
            "kind": tipo, "folio": folio, "amount": monto, "issue_date": emitido,
            "sha256": huella[:12], "cfdi_uuid": uuid_cfdi, "filename": voucher.original_filename})
        db.flush()
        return _ficha(db, orden, user_data)


def remove_voucher(id_voucher, payload: dict, user_data: dict) -> dict:
    """Quita un comprobante subido por error. Queda en la bitacora, con motivo.

    El archivo no se borra del disco: la bitacora dice que existio y el archivo es la
    prueba de lo que era.
    """
    actor = _actor(user_data)
    nota = _nota(payload.get("note"), obligatoria=True)
    with transaction_context() as db:
        voucher = db.scalars(
            select(PurchaseVoucher).where(
                PurchaseVoucher.id_purchase_voucher == _entero_positivo(id_voucher, "id"),
                PurchaseVoucher.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if voucher is None:
            raise AppError("errors.resource_not_found", 404)
        orden = _orden(db, voucher.id_purchase_order, for_update=True)
        if orden.order_status not in VOUCHER_REMOVABLE[voucher.kind]:
            raise AppError("errors.voucher_not_removable", 409, {
                "kind": voucher.kind, "order_status": orden.order_status})
        voucher.deletion_date = _ahora()
        _evento(db, orden, "voucher_removed", actor, nota=nota, detalle={
            "kind": voucher.kind, "folio": voucher.folio, "amount": voucher.amount,
            "sha256": voucher.sha256[:12]})
        db.flush()
        return _ficha(db, orden, user_data)


def voucher_content(id_voucher, user_data: dict, storage: SecureDocumentStorage):
    """(ruta, tipo, nombre) del archivo, para descargarlo."""
    _actor(user_data)
    with transaction_context() as db:
        voucher = db.scalars(
            select(PurchaseVoucher).where(
                PurchaseVoucher.id_purchase_voucher == _entero_positivo(id_voucher, "id"),
                PurchaseVoucher.deletion_date.is_(None),
            )
        ).first()
        if voucher is None:
            raise AppError("errors.resource_not_found", 404)
        orden = _orden(db, voucher.id_purchase_order)
        return (storage.resolve(voucher.file_path), voucher.mime_type,
                "%s-%s.%s" % (orden.folio, voucher.kind, voucher.extension))


# --- comprar ------------------------------------------------------------------

def purchase_order(id_order, payload: dict, user_data: dict) -> dict:
    """Marca la orden como comprada, con su comprobante y como se pago.

    El folio y el monto de la compra salen DEL comprobante subido, no de lo que se
    teclee aqui. Si el monto real pasa de lo autorizado mas la tolerancia, la orden
    no se compra: vuelve a autorizacion con el monto verdadero.
    """
    actor = _actor(user_data)
    fecha = _fecha_o_nada(payload.get("purchase_date"), "purchase_date")
    if fecha is None:
        raise AppError("errors.invalid_field", 400, {"field": "purchase_date"})
    if fecha > _hoy() + DATE_TOLERANCE:
        raise AppError("errors.invalid_field", 400, {"field": "purchase_date"})
    if fecha < _hoy() - PURCHASE_DATE_MAX_AGE:
        raise AppError("errors.invalid_field", 400, {"field": "purchase_date"})
    metodo = str(payload.get("payment_method") or "").strip().lower()
    if metodo not in PAYMENT_METHODS:
        raise AppError("errors.invalid_field", 400, {
            "field": "payment_method", "allowed": list(PAYMENT_METHODS)})
    referencia = _texto(payload.get("payment_reference"), "payment_reference", REFERENCE_MAX)
    if metodo in PAYMENT_NEEDS_REFERENCE and not referencia:
        # Una transferencia sin clave de rastreo o un cheque sin numero no se pueden
        # contrastar con el estado de cuenta.
        raise AppError("errors.invalid_field", 400, {"field": "payment_reference"})
    externo = str(payload.get("paid_externally") or "").strip().lower() in ("1", "true", "si", "yes")

    with transaction_context() as db:
        orden = _orden(db, id_order, for_update=True)
        if orden.order_status != "authorized":
            raise AppError("errors.order_not_authorized", 409, {"order_status": orden.order_status})
        evidencia = [v for v in _comprobantes(db, orden.id_purchase_order)
                     if v.kind in EVIDENCE_KINDS]
        if not evidencia:
            raise AppError("errors.purchase_needs_voucher", 409)
        comprobante = evidencia[0]
        monto = Decimal(comprobante.amount)
        politica = _politica(db)

        # Lo que la politica diga del monto REAL, no del cotizado.
        gerente = orden.requires_manager_purchase or (
            politica.manager_buys_above is not None and monto > politica.manager_buys_above)
        if gerente:
            _exigir_autorizar(db, user_data)
        elif orden.authorized_by is not None and int(orden.authorized_by) == actor:
            # Quien autoriza no compra, salvo lo que la politica reserva a gerencia.
            raise AppError("errors.purchase_same_person", 403, {"action": "purchase"})

        tope = (Decimal(orden.authorized_total) * (1 + Decimal(politica.overrun_percent) / 100)
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if monto > tope and monto > Decimal(politica.authorize_above):
            # Salio mas caro de lo autorizado: se vuelve a autorizar con el monto real.
            detalle = {
                "authorized_total": orden.authorized_total, "voucher_amount": monto,
                "limit": tope, "overrun_percent": politica.overrun_percent,
                "voucher_folio": comprobante.folio}
            orden.requires_authorization = True
            orden.requires_manager_purchase = gerente
            orden.quoted_total = monto
            orden.authorized_total = None
            orden.authorized_by = None
            orden.authorized_date = None
            _cambiar_estado(db, orden, "pending_authorization", "reauthorization_required",
                            actor, nota="El comprobante excede lo autorizado", detalle=detalle)
            db.flush()
            ficha = _ficha(db, orden, user_data)
            ficha["reauthorization_required"] = True
            return ficha

        orden.requires_manager_purchase = gerente
        orden.purchase_folio = comprobante.folio
        orden.purchase_date = fecha
        orden.total_amount = monto
        orden.payment_method = metodo
        orden.payment_reference = referencia
        orden.paid_externally = externo
        orden.purchased_by = actor
        orden.purchased_date = _ahora()
        _cambiar_estado(db, orden, "purchased", "purchased", actor, detalle={
            "folio": comprobante.folio, "amount": monto, "authorized_total": orden.authorized_total,
            "payment_method": metodo, "payment_reference": referencia,
            "paid_externally": externo, "id_purchase_voucher": comprobante.id_purchase_voucher})
        db.flush()
        ficha = _ficha(db, orden, user_data)
        ficha["reauthorization_required"] = False
        return ficha


# --- recibir --------------------------------------------------------------------

def receive_order(id_order, payload: dict, user_data: dict) -> dict:
    """Confirma que llego lo comprado, renglon por renglon y en las cantidades que llegaron.

    La recepcion es PARCIAL por naturaleza: el proveedor entrega en dos viajes y
    alguien tiene que poder decir "llegaron 60 de 100" sin cerrar la orden. Cada
    llamada SUMA a lo ya recibido; la orden pasa a `received` cuando todos los
    renglones estan completos y se queda en `partially_received` mientras falte.

    Quien recibe lo decide la capacidad `purchase_receive` en el Gestor (Almacen, o
    Compras si se le concede). Ya no hay regla por persona: quien compro puede
    confirmar que llego, si su rol tiene la capacidad (2026-10-19, pedido de Adser).

    Solo confirma CANTIDAD. No da entrada al inventario: lo comprado es, casi
    siempre, material de obra en texto libre -sin producto ni ubicacion a donde
    meterlo-, y meterlo por la fuerza inventaria lo que no se inventaria.
    """
    actor = _actor(user_data)
    nota = _nota(payload.get("note"))
    datos = payload.get("lines")
    if not isinstance(datos, list) or not datos:
        raise AppError("errors.invalid_field", 400, {"field": "lines"})
    # Una llave por intento: el doble clic o el reintento de red no suma dos veces.
    llave = re.sub(r"[^A-Za-z0-9_.:-]", "", str(payload.get("idempotency_key") or ""))[:80]

    with transaction_context() as db:
        _exigir_recibir(db, user_data)
        orden = _orden(db, id_order, for_update=True)
        if llave and db.scalar(select(PurchaseEvent.id_purchase_event).where(
                PurchaseEvent.id_purchase_order == orden.id_purchase_order,
                PurchaseEvent.event_type.in_(("received", "partially_received")),
                PurchaseEvent.detail.like('%"key": "' + llave + '"%')).limit(1)):
            ficha = _ficha(db, orden, user_data)
            ficha["replayed"] = True
            return ficha
        if orden.order_status not in RECEIVABLE_STATES:
            raise AppError("errors.order_not_receivable", 409,
                           {"order_status": orden.order_status})

        renglones ={r.id_purchase_order_line: r for r in _renglones(db, orden.id_purchase_order)}
        vistos = set()
        llegado = []
        for dato in datos:
            if not isinstance(dato, dict):
                raise AppError("errors.invalid_field", 400, {"field": "lines"})
            id_renglon = _entero_positivo(dato.get("id_purchase_order_line"),
                                          "id_purchase_order_line")
            if id_renglon in vistos:
                raise AppError("errors.order_duplicate_line", 409,
                               {"id_purchase_order_line": id_renglon})
            vistos.add(id_renglon)
            renglon = renglones.get(id_renglon)
            if renglon is None:
                raise AppError("errors.resource_not_found", 404)
            cantidad = _cantidad(dato.get("quantity"))
            if int(renglon.quantity_received) + cantidad > int(renglon.quantity):
                # Recibir de mas es una discrepancia con la factura, no una recepcion:
                # se rechaza para que alguien la mire en vez de esconderla.
                raise AppError("errors.order_receive_exceeds", 409, {
                    "id_purchase_order_line": id_renglon,
                    "ordered": int(renglon.quantity),
                    "already_received": int(renglon.quantity_received)})
            llegado.append((renglon, cantidad))

        for renglon, cantidad in llegado:
            renglon.quantity_received = int(renglon.quantity_received) + cantidad

        completa = all(int(r.quantity_received) >= int(r.quantity) for r in renglones.values())
        nuevo = "received" if completa else "partially_received"
        _cambiar_estado(db, orden, nuevo, "received" if completa else "partially_received",
                        actor, nota=nota, detalle={"key": llave or None, "lines": [
                            {"id_purchase_order_line": r.id_purchase_order_line,
                             "description": r.description, "received_now": c,
                             "received_total": int(r.quantity_received),
                             "ordered": int(r.quantity)} for r, c in llegado]})
        db.flush()
        return _ficha(db, orden, user_data)


# --- avisos ---------------------------------------------------------------------

def _usuarios_con_capacidad(db, capacidad: str) -> set[int]:
    """Quienes pueden EDITAR esa capacidad: a ellos les toca el siguiente paso."""
    permisos = db.scalars(
        select(EntityPermission.id_permission).where(
            EntityPermission.entity_name == capacidad,
            EntityPermission.scope_update != 0,
            EntityPermission.deletion_date.is_(None))).all()
    if not permisos:
        return set()
    return {int(i) for i in db.scalars(
        select(User.id_user).where(User.id_permission.in_(list(permisos)),
                                   User.deletion_date.is_(None))).all()}


def _de_los_proyectos(db, ids_proyecto) -> set[int]:
    if not ids_proyecto:
        return set()
    filas = db.execute(select(Proyect.id_supervisor, Proyect.leader)
                       .where(Proyect.id_proyect.in_(list(ids_proyecto)))).all()
    return {int(u) for fila in filas for u in fila if u}


# evento -> (tipo de aviso, titulo, quien lo recibe). El mensaje lo arma `notificar_orden`.
_AVISOS = {
    "por_autorizar": ("purchase_order_pending", "{folio} espera autorizacion"),
    "autorizada": ("purchase_order_authorized", "{folio} autorizada: ya se puede comprar"),
    "rechazada": ("purchase_order_rejected", "{folio} fue rechazada"),
    "comprada": ("purchase_order_purchased", "{folio} comprada: viene en camino"),
    "recibida": ("purchase_order_received", "{folio} recibida"),
    "recibida_en_parte": ("purchase_order_partially_received", "{folio} recibida en parte"),
}


def notificar_orden(evento: str, ficha: dict, actor_id: int) -> None:
    """Avisa (campana) a quien le toca el siguiente paso de la orden.

    Se llama desde la RUTA, ya cerrada la transaccion: `create_notification` abre la
    suya. Un fallo al avisar nunca revierte lo que se hizo (mismo criterio que los
    avisos del vale). Quien hizo la accion no se avisa a si mismo.
    """
    from app.services.notification_service import create_notification

    try:
        if evento not in _AVISOS:
            return
        tipo, titulo = _AVISOS[evento]
        folio = ficha.get("folio") or "Orden"
        with transaction_context() as db:
            if evento == "por_autorizar":
                destinatarios = _usuarios_con_capacidad(db, AUTHORIZE_CAPABILITY)
                mensaje = "La orden %s espera autorizacion." % folio
                if ficha.get("exceeds_budget"):
                    mensaje = ("La orden %s excede el presupuesto de un proyecto "
                               "y espera autorizacion." % folio)
            elif evento == "autorizada":
                destinatarios = {ficha.get("created_by")}
                mensaje = "La orden %s fue autorizada; ya puede comprarse." % folio
            elif evento == "rechazada":
                destinatarios = {ficha.get("created_by")}
                mensaje = "La orden %s fue rechazada: %s" % (
                    folio, ficha.get("authorization_note") or "sin motivo")
            else:  # comprada / recibida / recibida_en_parte
                ids_proyecto = {l.get("id_proyect") for l in ficha.get("lines") or []
                                if l.get("id_proyect")}
                destinatarios = ({ficha.get("created_by"), ficha.get("purchased_by")}
                                 | _de_los_proyectos(db, ids_proyecto))
            if evento == "comprada":
                # NO se avisa a todo el almacen: el rol Almacenista lo llevan decenas de
                # personas (34 en Adser) y un aviso a todas es ruido. Quien necesita saber
                # que el material viene en camino es quien lo espera; el almacen la ve en
                # el filtro "Compradas" y es quien registra la recepcion.
                mensaje = "La orden %s ya se compro: el material viene en camino." % folio
            elif evento == "recibida":
                mensaje = "Llego todo lo de la orden %s." % folio
            elif evento == "recibida_en_parte":
                mensaje = "Llego una parte de la orden %s; aun falta material." % folio
        for destino in {int(d) for d in destinatarios if d} - {int(actor_id)}:
            create_notification(
                id_user_recipient=destino, id_user_sender=actor_id,
                notification_type=tipo, title=titulo.format(folio=folio), message=mensaje,
                metadata={"id_purchase_order": ficha.get("id_purchase_order")},
                target_entity="purchase_order", target_id=ficha.get("id_purchase_order"),
                created_by=actor_id)
    except Exception:
        pass
    if evento in ("recibida", "recibida_en_parte"):
        _avisar_material_completo_de(ficha, actor_id)


def _avisar_material_completo_de(ficha: dict, actor_id: int) -> None:
    """Tras recibir material, avisa de los proyectos a los que ya les llego todo.

    El aviso por orden de arriba dice que llego algo de ESA orden; el del proyecto
    dice que ya no falta nada de lo que pidio, que es lo que necesita quien lo
    lleva para saber que puede completarlo.
    """
    try:
        from app.services.project_management_service import avisar_material_completo

        ids = {l.get("id_proyect") for l in ficha.get("lines") or [] if l.get("id_proyect")}
        if ids:
            avisar_material_completo(ids, int(actor_id))
    except Exception:
        pass
