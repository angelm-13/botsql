"""El presupuesto de compras de cada proyecto, autorizado por gerencia.

Que protege
-----------
Gerencia fija cuanto se puede gastar en compras para un proyecto. Cada orden que arma
Compras se mide contra ese tope ANTES de autorizarse:

* **Comprometido** = lo que las ordenes vivas del proyecto ya piden o gastaron: por
  autorizar, autorizadas, compradas, recibidas y cerradas. Los borradores, las rechazadas
  y las canceladas no comprometen nada (una cancelada suelta lo que sostenia).
* Si lo comprometido MAS lo que pide la orden pasa del presupuesto, la orden queda
  `exceeds_budget`: aunque su monto este debajo del limite normal de autorizacion, no
  se autoriza sola. Solo quien autoriza la libera, con un motivo por escrito, y no puede
  ser quien la capturo (la misma regla de siempre).
* Un proyecto SIN presupuesto no tiene tope: se rige solo por la politica de montos.
  Es un tope que gerencia decide poner, no una prohibicion de comprar.
* Presupuesto y orden en monedas distintas no se pueden comparar (no hay tipo de cambio
  en la orden): la orden se trata como excedida y la libera quien autoriza.

Fijar o cambiar un presupuesto exige la misma capacidad que fijar la politica de montos
(`purchase_policy`, que Compras solo consulta): quien necesita el dinero no decide cuanto
tiene. Cada cambio deja renglon en `purchase_budget_event`, que solo se agrega.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlalchemy import func, select

from app.models import (
    Proyect, PurchaseBudget, PurchaseBudgetEvent, PurchaseOrder, PurchaseOrderLine, User,
)
from app.models.session import transaction_context
from app.services.proyect_material_need_service import _actor, _entero_positivo, _texto
from app.utils.errors import AppError

# Lo que cuenta como dinero ya pedido o gastado.
ESTADOS_QUE_COMPROMETEN = (
    "pending_authorization", "authorized", "purchased", "partially_received", "received",
    "closed",
)
MONEDAS = ("MXN", "USD")
MAX_PRESUPUESTO = Decimal("99999999999.99")
CENTAVOS = Decimal("0.01")


def _dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _importe_de_renglon(renglon) -> Decimal:
    if renglon.unit_cost is None:
        return Decimal("0")
    return Decimal(renglon.quantity) * Decimal(renglon.unit_cost)


def comprometido(db, ids_proyecto, *, moneda: str, excepto_orden: int | None = None) -> dict[int, Decimal]:
    """Lo comprometido por proyecto, en esa moneda, sin contar `excepto_orden`."""
    ids = {int(i) for i in ids_proyecto if i}
    if not ids:
        return {}
    consulta = (
        select(PurchaseOrderLine.id_proyect,
               func.coalesce(func.sum(PurchaseOrderLine.quantity * PurchaseOrderLine.unit_cost), 0))
        .join(PurchaseOrder, PurchaseOrder.id_purchase_order == PurchaseOrderLine.id_purchase_order)
        .where(
            PurchaseOrderLine.id_proyect.in_(ids),
            PurchaseOrderLine.deletion_date.is_(None),
            PurchaseOrderLine.unit_cost.isnot(None),
            PurchaseOrder.deletion_date.is_(None),
            PurchaseOrder.order_status.in_(ESTADOS_QUE_COMPROMETEN),
            PurchaseOrder.currency == moneda,
        )
        .group_by(PurchaseOrderLine.id_proyect)
    )
    if excepto_orden is not None:
        consulta = consulta.where(PurchaseOrder.id_purchase_order != int(excepto_orden))
    return {int(i): _dinero(total) for i, total in db.execute(consulta).all()}


def evaluar_orden(db, orden: PurchaseOrder, renglones) -> list[dict]:
    """Una fila por proyecto de la orden QUE TENGA presupuesto.

    Cada fila dice el presupuesto, lo ya comprometido por las demas ordenes, lo que pide
    esta, lo que quedaria y si se pasa. Vacio si ningun proyecto de la orden tiene tope.
    """
    pedido: dict[int, Decimal] = {}
    for renglon in renglones:
        if renglon.id_proyect and renglon.unit_cost is not None:
            llave = int(renglon.id_proyect)
            pedido[llave] = pedido.get(llave, Decimal("0")) + _importe_de_renglon(renglon)
    if not pedido:
        return []
    presupuestos = {int(b.id_proyect): b for b in db.scalars(
        select(PurchaseBudget).where(PurchaseBudget.id_proyect.in_(list(pedido))))}
    if not presupuestos:
        return []
    proyectos = {int(i): (f, t) for i, f, t in db.execute(
        select(Proyect.id_proyect, Proyect.folio, Proyect.title)
        .where(Proyect.id_proyect.in_(list(presupuestos))))}
    moneda_orden = str(orden.currency or "MXN").upper()
    filas = []
    for id_proyecto in sorted(presupuestos):
        presupuesto = presupuestos[id_proyecto]
        pide = _dinero(pedido[id_proyecto])
        ya = comprometido(db, [id_proyecto], moneda=presupuesto.currency,
                          excepto_orden=orden.id_purchase_order).get(id_proyecto, Decimal("0"))
        monto = _dinero(presupuesto.amount)
        folio, titulo = proyectos.get(id_proyecto, (None, None))
        fila = {
            "id_proyect": id_proyecto, "folio": folio, "title": titulo,
            "budget": float(monto), "currency": presupuesto.currency,
            "committed": float(ya), "requested": float(pide),
        }
        if moneda_orden != presupuesto.currency:
            fila.update({"remaining_after": None, "over_by": None, "exceeds": True,
                         "reason": "currency_mismatch"})
        else:
            despues = ya + pide
            fila.update({
                "remaining_after": float(monto - despues),
                "over_by": float(max(despues - monto, Decimal("0"))),
                "exceeds": despues > monto, "reason": "over_budget" if despues > monto else None,
            })
        filas.append(fila)
    return filas


def excede(evaluacion: list[dict]) -> bool:
    return any(f["exceeds"] for f in evaluacion)


def resumen_del_exceso(evaluacion: list[dict]) -> str:
    """Texto corto para la nota del evento y el aviso a quien autoriza."""
    partes = []
    for f in evaluacion:
        if not f["exceeds"]:
            continue
        nombre = f.get("folio") or f.get("title") or "#%s" % f["id_proyect"]
        if f.get("reason") == "currency_mismatch":
            partes.append("%s (moneda distinta al presupuesto)" % nombre)
        else:
            partes.append("%s (se pasa por %.2f %s)" % (nombre, f["over_by"], f["currency"]))
    return "Excede el presupuesto de: " + "; ".join(partes) if partes else ""


# --- consultar y fijar -----------------------------------------------------------

def _fila_de_proyecto(id_proyecto, presupuesto, proyecto, comprometidos, nombres) -> dict:
    monto = _dinero(presupuesto.amount) if presupuesto is not None else None
    ya = comprometidos.get(int(id_proyecto), Decimal("0"))
    disponible = (monto - ya) if monto is not None else None
    return {
        "id_proyect": int(id_proyecto),
        "folio": proyecto[0] if proyecto else None,
        "title": proyecto[1] if proyecto else None,
        "proyect_status": proyecto[2] if proyecto else None,
        "budget": float(monto) if monto is not None else None,
        "currency": presupuesto.currency if presupuesto is not None else "MXN",
        "committed": float(ya),
        "available": float(disponible) if disponible is not None else None,
        "percent_used": (float((ya / monto * 100).quantize(CENTAVOS)) if monto else None),
        "exceeded": bool(monto is not None and ya > monto),
        "note": presupuesto.note if presupuesto is not None else None,
        "updated_by": presupuesto.updated_by if presupuesto is not None else None,
        "updated_by_name": nombres.get(int(presupuesto.updated_by)) if presupuesto is not None else None,
        "last_update_date": (presupuesto.last_update_date.isoformat()
                             if presupuesto is not None and presupuesto.last_update_date else None),
    }


def list_budgets(user_data: dict, *, q: str | None = None, solo_con_presupuesto: bool = False) -> dict:
    """Los proyectos con presupuesto, mas los que ya estan comprando sin tenerlo.

    Estos ultimos salen con `budget: null` para que gerencia vea donde falta ponerle tope.
    """
    _actor(user_data)
    with transaction_context() as db:
        presupuestos = {int(b.id_proyect): b for b in db.scalars(select(PurchaseBudget))}
        con_compras = {int(i) for (i,) in db.execute(
            select(PurchaseOrderLine.id_proyect).join(
                PurchaseOrder, PurchaseOrder.id_purchase_order == PurchaseOrderLine.id_purchase_order)
            .where(PurchaseOrderLine.id_proyect.isnot(None),
                   PurchaseOrderLine.deletion_date.is_(None),
                   PurchaseOrder.deletion_date.is_(None),
                   PurchaseOrder.order_status.in_(ESTADOS_QUE_COMPROMETEN))
            .distinct())}
        ids = set(presupuestos) | (set() if solo_con_presupuesto else con_compras)
        if not ids:
            return {"items": [], "total": 0}
        proyectos = {int(i): (f, t, s) for i, f, t, s in db.execute(
            select(Proyect.id_proyect, Proyect.folio, Proyect.title, Proyect.proyect_status)
            .where(Proyect.id_proyect.in_(ids), Proyect.deletion_date.is_(None)))}
        # Lo comprometido se mide en la moneda de cada presupuesto (MXN si no hay).
        comprometidos: dict[int, Decimal] = {}
        for moneda in MONEDAS:
            en_moneda = [i for i in proyectos if (presupuestos[i].currency if i in presupuestos else "MXN") == moneda]
            comprometidos.update(comprometido(db, en_moneda, moneda=moneda))
        nombres = {int(i): n for i, n in db.execute(
            select(User.id_user, func.coalesce(User.full_name, User.username))
            .where(User.id_user.in_({int(b.updated_by) for b in presupuestos.values()} or {0})))}
        texto = " ".join(str(q or "").split()).lower()
        items = []
        for id_proyecto in sorted(proyectos, reverse=True):
            fila = _fila_de_proyecto(id_proyecto, presupuestos.get(id_proyecto),
                                     proyectos[id_proyecto], comprometidos, nombres)
            if texto and texto not in ("%s %s" % (fila["folio"] or "", fila["title"] or "")).lower():
                continue
            items.append(fila)
        return {"items": items, "total": len(items)}


def get_budget(id_proyect, user_data: dict) -> dict:
    _actor(user_data)
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    resultado = list_budgets(user_data)
    for fila in resultado["items"]:
        if fila["id_proyect"] == id_proyecto:
            return fila
    with transaction_context() as db:
        proyecto = db.get(Proyect, id_proyecto)
        if proyecto is None or proyecto.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        return _fila_de_proyecto(id_proyecto, None,
                                 (proyecto.folio, proyecto.title, proyecto.proyect_status), {}, {})


def set_budget(id_proyect, payload: dict, user_data: dict) -> dict:
    """Fija o cambia el presupuesto de un proyecto. Deja constancia de quien y de cuanto a cuanto."""
    actor = _actor(user_data)
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    try:
        monto = _dinero(payload.get("amount"))
    except (InvalidOperation, ValueError) as error:
        raise AppError("errors.invalid_field", 400, {"field": "amount"}) from error
    if payload.get("amount") in (None, "") or monto < 0 or monto > MAX_PRESUPUESTO:
        raise AppError("errors.invalid_field", 400, {"field": "amount"})
    nota = _texto(payload.get("note"), "note", 300, obligatorio=False)
    moneda = str(payload.get("currency") or "MXN").strip().upper()
    if moneda not in MONEDAS:
        raise AppError("errors.invalid_field", 400, {"field": "currency", "allowed": list(MONEDAS)})

    with transaction_context() as db:
        proyecto = db.get(Proyect, id_proyecto)
        if proyecto is None or proyecto.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        presupuesto = db.scalars(
            select(PurchaseBudget).where(PurchaseBudget.id_proyect == id_proyecto).with_for_update()
        ).first()
        antes = _dinero(presupuesto.amount) if presupuesto is not None else None
        if presupuesto is None:
            presupuesto = PurchaseBudget(id_proyect=id_proyecto, amount=monto, currency=moneda,
                                         note=nota, updated_by=actor)
            db.add(presupuesto)
        else:
            if antes == monto and presupuesto.currency == moneda and (presupuesto.note or None) == (nota or None):
                return get_budget(id_proyecto, user_data)
            presupuesto.amount = monto
            presupuesto.currency = moneda
            presupuesto.note = nota
            presupuesto.updated_by = actor
        db.add(PurchaseBudgetEvent(id_proyect=id_proyecto, amount_before=antes,
                                   amount_after=monto, note=nota, created_by=actor))
        db.flush()
    return get_budget(id_proyecto, user_data)


def budget_history(id_proyect, user_data: dict) -> dict:
    _actor(user_data)
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    with transaction_context() as db:
        eventos = list(db.scalars(
            select(PurchaseBudgetEvent).where(PurchaseBudgetEvent.id_proyect == id_proyecto)
            .order_by(PurchaseBudgetEvent.id_purchase_budget_event.desc())))
        nombres = {int(i): n for i, n in db.execute(
            select(User.id_user, func.coalesce(User.full_name, User.username))
            .where(User.id_user.in_({int(e.created_by) for e in eventos} or {0})))}
        return {"id_proyect": id_proyecto, "items": [
            {**e.serialize(), "created_by_name": nombres.get(int(e.created_by))} for e in eventos]}
