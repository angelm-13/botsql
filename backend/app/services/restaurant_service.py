from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.restaurant import (
    RestaurantCashSession,
    RestaurantCategory,
    RestaurantDish,
    RestaurantGuisado,
    RestaurantInventoryItem,
    RestaurantInventoryMovement,
    RestaurantOrder,
    RestaurantOrderItem,
    RestaurantRecipeItem,
    RestaurantReservation,
    RestaurantTable,
    RestaurantVisit,
    RestaurantWaiter,
)
from app.security.audit import audit_event
from app.services.restaurant_rules import ESTADO_DE_VENTA
from app.utils.errors import AppError


DISH_CATEGORIES = {
    "taco",
    "gordita",
    "quesadilla",
    "platillo_dia",
    "postre",
    "agua",
    "refresco",
    "cafe",
    "dulce",
}
INVENTORY_MOVEMENT_TYPES = {"entrada", "salida", "merma", "ajuste"}
PAYMENT_METHODS = {"efectivo", "tarjeta", "transferencia", "mixto"}
ORDER_TRANSITIONS = {
    "borrador": "pedido",
    "pedido": "en_preparacion",
    "en_preparacion": "listo_para_entrega",
    "listo_para_entrega": "entregado",
}


def _decimal(value, field: str, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        parsed = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if parsed < minimum:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return parsed


def _integer(value, field: str, minimum: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if parsed < minimum:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return parsed


def _required_text(payload: dict, field: str, limit: int) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return value[:limit]


def _not_found() -> AppError:
    return AppError("errors.resource_not_found", 404)


def _split_exact(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Reparte `amount` en proporcion a `weights` sumando exactamente `amount`.

    Se redondea cada parte a dos decimales y la diferencia acumulada por
    redondeo se carga a la ultima, para que sum(partes) == amount siempre.
    Si todos los pesos son cero, reparte en partes iguales.
    """
    if not weights:
        return []
    total_weight = sum(weights)
    if total_weight == 0:
        weights = [Decimal("1")] * len(weights)
        total_weight = Decimal(len(weights))
    parts = [
        (amount * weight / total_weight).quantize(Decimal("0.01")) for weight in weights
    ]
    parts[-1] += amount - sum(parts)
    return parts


def _slug(value: str) -> str:
    """Normaliza a slug: minusculas, sin acentos, con guion bajo."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", normalized.lower())).strip("_")


def _order_query(project_id: int):
    return (
        select(RestaurantOrder)
        .where(RestaurantOrder.id_proyect == project_id, RestaurantOrder.deletion_date.is_(None))
        .options(
            selectinload(RestaurantOrder.visit).selectinload(RestaurantVisit.table),
            selectinload(RestaurantOrder.items).selectinload(RestaurantOrderItem.dish),
            selectinload(RestaurantOrder.items).selectinload(RestaurantOrderItem.guisado_1),
            selectinload(RestaurantOrder.items).selectinload(RestaurantOrderItem.guisado_2),
        )
    )


class RestaurantService:
    def __init__(self, db: Session, project_id: int, user_id: int):
        self.db = db
        self.project_id = int(project_id)
        self.user_id = int(user_id)

    @staticmethod
    def _puente_de_inventario():
        """El puente al libro del nucleo, importado al usarse.

        Diferido y no arriba porque `inventory_service` arrastra los modelos del
        nucleo, y este modulo se importa desde el registro de blueprints: un
        import circular en el arranque es un fallo que no se ve hasta que la
        aplicacion no levanta.
        """
        from app.services.restaurant_inventory_bridge import reflejar_movimiento

        return reflejar_movimiento

    def _usuario(self) -> dict:
        """El actor, en la forma que espera el nucleo.

        `apply_movement_in_session` recibe el mismo diccionario que las rutas
        del core -- de ahi saca quien hizo el movimiento y su proyecto -- y este
        servicio solo guarda los dos numeros sueltos.
        """
        return {"id_user": self.user_id, "id_proyect": self.project_id}

    def _audit(self, entity: str, action: str, metadata: dict | None = None) -> None:
        """Registra un cambio administrativo en la bitacora del core.

        Reusa la bitacora de tyakxa (app/security/audit.py) en vez de una tabla
        propia del restaurante: es la misma necesidad y ya existe la
        consulta por entity_name.
        """
        audit_event(
            self.db,
            {"id_user": self.user_id},
            event_type="restaurant",
            entity_name=f"restaurant_{entity}",
            action=action,
            metadata={"id_proyect": self.project_id, **(metadata or {})},
        )

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        """La bitacora del restaurante, leida de la bitacora unica.

        Antes salia de `audit_log`, una segunda tabla que existia solo porque
        `event_log.action` no admitia verbos fuera del CRUD. Fundidas las dos
        (migracion 20260911120000), esto filtra por `table_name`, que es lo que
        distingue un asiento del restaurante de cualquier otro.

        Se conservan las claves que la pantalla ya leia -- `id_audit_log`,
        `entity_name` -- para no arrastrar el cambio de tabla hasta el front.
        """
        from app.models.event_log import EventLog

        rows = self.db.scalars(
            select(EventLog)
            .where(
                EventLog.table_name.like("restaurant_%"),
                EventLog.id_proyect == self.project_id,
                EventLog.deletion_date.is_(None),
            )
            .order_by(EventLog.creation_date.desc())
            .limit(max(1, min(int(limit or 100), 500)))
        ).all()
        return [
            {
                "id_audit_log": row.id_event_log,
                "id_user": row.created_by,
                "event_type": (row.after_value or {}).get("event_type", "restaurant"),
                "entity_name": row.table_name,
                "action": row.event_detail or row.action,
                "metadata_json": row.after_value or {},
                "creation_date": (row.creation_date.isoformat()
                                  if row.creation_date else None),
            }
            for row in rows
        ]

    def list_tables(self) -> list[dict]:
        tables = self.db.scalars(
            select(RestaurantTable)
            .where(
                RestaurantTable.id_proyect == self.project_id,
                RestaurantTable.deletion_date.is_(None),
                RestaurantTable.is_active.is_(True),
            )
            .order_by(RestaurantTable.number)
        ).all()
        visits = self.db.scalars(
            select(RestaurantVisit)
            .where(
                RestaurantVisit.id_proyect == self.project_id,
                RestaurantVisit.status == "active",
                RestaurantVisit.deletion_date.is_(None),
                # Las ordenes para llevar no ocupan mesa (su
                # id_restaurant_table es NULL) y no van en este mapa.
                RestaurantVisit.id_restaurant_table.is_not(None),
            )
        ).all()
        occupied = {visit.id_restaurant_table: visit for visit in visits}
        result = []
        for table in tables:
            row = table.serialize()
            visit = occupied.get(table.id_restaurant_table)
            row.update(
                occupied=visit is not None,
                visit_id=visit.id_restaurant_visit if visit else None,
                diners_count=visit.diners_count if visit else 0,
            )
            result.append(row)
        return result

    def list_visits(self, status: str | None = None) -> list[dict]:
        query = (
            select(RestaurantVisit)
            .where(
                RestaurantVisit.id_proyect == self.project_id,
                RestaurantVisit.deletion_date.is_(None),
            )
            .options(
                selectinload(RestaurantVisit.table),
                selectinload(RestaurantVisit.orders)
                .selectinload(RestaurantOrder.items)
                .selectinload(RestaurantOrderItem.dish),
                selectinload(RestaurantVisit.orders)
                .selectinload(RestaurantOrder.items)
                .selectinload(RestaurantOrderItem.guisado_1),
                selectinload(RestaurantVisit.orders)
                .selectinload(RestaurantOrder.items)
                .selectinload(RestaurantOrderItem.guisado_2),
            )
            .order_by(RestaurantVisit.opened_at.desc())
        )
        if status:
            query = query.where(RestaurantVisit.status == status)
        return [visit.serialize() for visit in self.db.scalars(query).unique().all()]

    def get_visit(self, visit_id: int) -> dict:
        visits = self.list_visits()
        visit = next((row for row in visits if row["id_restaurant_visit"] == visit_id), None)
        if not visit:
            raise _not_found()
        return visit

    def create_visit(self, payload: dict) -> dict:
        table_id = _integer(payload.get("id_restaurant_table"), "id_restaurant_table")
        diners = _integer(payload.get("diners_count", 1), "diners_count")
        table = self.db.scalar(
            select(RestaurantTable).where(
                RestaurantTable.id_restaurant_table == table_id,
                RestaurantTable.id_proyect == self.project_id,
                RestaurantTable.is_active.is_(True),
                RestaurantTable.deletion_date.is_(None),
            )
        )
        if not table:
            raise _not_found()
        existing = self.db.scalar(
            select(RestaurantVisit).where(
                RestaurantVisit.id_restaurant_table == table_id,
                RestaurantVisit.status == "active",
                RestaurantVisit.deletion_date.is_(None),
            )
        )
        if existing:
            raise AppError("restaurant.table_occupied", 409)
        waiter_id = payload.get("id_restaurant_waiter")
        if waiter_id:
            waiter = self._waiter(_integer(waiter_id, "id_restaurant_waiter"))
            active_tables = self.db.scalar(
                select(func.count(RestaurantVisit.id_restaurant_visit)).where(
                    RestaurantVisit.id_restaurant_waiter == waiter.id_restaurant_waiter,
                    RestaurantVisit.status == "active",
                    RestaurantVisit.deletion_date.is_(None),
                )
            )
            if int(active_tables or 0) >= waiter.max_tables:
                raise AppError("restaurant.waiter_table_limit", 409)
        visit = RestaurantVisit(
            id_proyect=self.project_id,
            id_restaurant_table=table_id,
            id_restaurant_waiter=waiter_id,
            service_type="mesa",
            diners_count=diners,
            status="active",
            created_by=self.user_id,
        )
        self.db.add(visit)
        self.db.flush()
        for diner_index in range(1, diners + 1):
            self.db.add(
                RestaurantOrder(
                    id_proyect=self.project_id,
                    id_restaurant_visit=visit.id_restaurant_visit,
                    diner_index=diner_index,
                    id_restaurant_waiter=waiter_id,
                    status="borrador",
                    created_by=self.user_id,
                )
            )
        self.db.flush()
        return self.get_visit(visit.id_restaurant_visit)

    def create_takeout_visit(self, payload: dict) -> dict:
        """Abre una orden para llevar: sin mesa, con folio diario.

        El folio se calcula por proyecto y dia de servicio. La fecha la
        manda el cliente como tz_offset_minutes para que el corte del folio
        ocurra a la medianoche LOCAL del restaurante y no a la del servidor,
        que puede estar en otra zona.
        """
        offset = payload.get("tz_offset_minutes", 0)
        try:
            offset_minutes = int(offset)
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "tz_offset_minutes"}) from exc
        if abs(offset_minutes) > 14 * 60:
            raise AppError("errors.invalid_field", 400, {"field": "tz_offset_minutes"})
        service_day = (datetime.utcnow() - timedelta(minutes=offset_minutes)).date()

        waiter_id = payload.get("id_restaurant_waiter")
        if waiter_id:
            waiter_id = self._waiter(_integer(waiter_id, "id_restaurant_waiter")).id_restaurant_waiter
        last_number = self.db.scalar(
            select(func.max(RestaurantVisit.daily_number)).where(
                RestaurantVisit.id_proyect == self.project_id,
                RestaurantVisit.service_type == "para_llevar",
                RestaurantVisit.service_date == service_day,
                RestaurantVisit.deletion_date.is_(None),
            )
        )
        visit = RestaurantVisit(
            id_proyect=self.project_id,
            id_restaurant_table=None,
            id_restaurant_waiter=waiter_id,
            service_type="para_llevar",
            customer_name=_required_text(payload, "customer_name", 140),
            daily_number=int(last_number or 0) + 1,
            service_date=service_day,
            diners_count=1,
            status="active",
            created_by=self.user_id,
        )
        self.db.add(visit)
        self.db.flush()
        # Una orden para llevar es un solo "comensal": no se reparte cuenta.
        self.db.add(
            RestaurantOrder(
                id_proyect=self.project_id,
                id_restaurant_visit=visit.id_restaurant_visit,
                diner_index=1,
                id_restaurant_waiter=waiter_id,
                status="borrador",
                created_by=self.user_id,
            )
        )
        self.db.flush()
        return self.get_visit(visit.id_restaurant_visit)

    def add_diner(self, visit_id: int) -> dict:
        visit = self._visit(visit_id)
        if visit.status != "active":
            raise AppError("restaurant.visit_closed", 409)
        next_index = max((order.diner_index for order in visit.orders), default=0) + 1
        self.db.add(
            RestaurantOrder(
                id_proyect=self.project_id,
                id_restaurant_visit=visit.id_restaurant_visit,
                diner_index=next_index,
                id_restaurant_waiter=visit.id_restaurant_waiter,
                status="borrador",
                created_by=self.user_id,
            )
        )
        visit.diners_count += 1
        self.db.flush()
        return self.get_visit(visit_id)

    def remove_diner(self, visit_id: int, diner_index: int) -> dict:
        visit = self._visit(visit_id)
        order = next((item for item in visit.orders if item.diner_index == diner_index), None)
        if not order:
            raise _not_found()
        if order.status != "borrador" or order.items:
            raise AppError("restaurant.diner_not_removable", 409)
        self.db.delete(order)
        visit.diners_count = max(visit.diners_count - 1, 0)
        self.db.flush()
        return self.get_visit(visit_id)

    def close_visit(self, visit_id: int) -> dict:
        visit = self._visit(visit_id)
        if any(order.items and order.status != "pagado" for order in visit.orders):
            raise AppError("restaurant.unpaid_orders", 409)
        visit.status = "closed"
        visit.closed_at = datetime.utcnow()
        self.db.flush()
        return self.get_visit(visit_id)

    def list_menu(self, category: str | None = None, only_today: bool = False) -> dict:
        query = select(RestaurantDish).where(
            RestaurantDish.id_proyect == self.project_id,
            RestaurantDish.is_active.is_(True),
            RestaurantDish.deletion_date.is_(None),
        )
        if category:
            query = query.where(RestaurantDish.category == category)
        dishes = self.db.scalars(query.order_by(RestaurantDish.category, RestaurantDish.title)).all()
        if only_today:
            dishes = [dish for dish in dishes if dish.is_available_today()]
        guisados = self.db.scalars(
            select(RestaurantGuisado)
            .where(
                RestaurantGuisado.id_proyect == self.project_id,
                RestaurantGuisado.is_active.is_(True),
                RestaurantGuisado.deletion_date.is_(None),
            )
            .order_by(RestaurantGuisado.name)
        ).all()
        return {
            "dishes": [dish.serialize() for dish in dishes],
            "guisados": [guisado.serialize() for guisado in guisados],
            "categories": self.list_categories(),
        }

    def list_categories(self) -> list[dict]:
        """Catalogo de categorias del proyecto.

        Si el proyecto todavia no definio ninguna, devuelve el set fijo
        historico (DISH_CATEGORIES) como catalogo de solo lectura, para que
        una instalacion existente siga funcionando sin sembrar nada.
        """
        rows = self.db.scalars(
            select(RestaurantCategory)
            .where(
                RestaurantCategory.id_proyect == self.project_id,
                RestaurantCategory.is_active.is_(True),
                RestaurantCategory.deletion_date.is_(None),
            )
            .order_by(RestaurantCategory.sort_order, RestaurantCategory.label)
        ).all()
        if rows:
            return [row.serialize() for row in rows]
        return [
            {"slug": slug, "label": slug.replace("_", " ").title(), "icon": "plate", "sort_order": 100}
            for slug in sorted(DISH_CATEGORIES)
        ]

    def _allowed_categories(self) -> set[str]:
        rows = self.db.scalars(
            select(RestaurantCategory.slug).where(
                RestaurantCategory.id_proyect == self.project_id,
                RestaurantCategory.is_active.is_(True),
                RestaurantCategory.deletion_date.is_(None),
            )
        ).all()
        return set(rows) if rows else set(DISH_CATEGORIES)

    def save_category(self, payload: dict, category_id: int | None = None) -> dict:
        if category_id:
            category = self.db.scalar(
                select(RestaurantCategory).where(
                    RestaurantCategory.id_restaurant_category == category_id,
                    RestaurantCategory.id_proyect == self.project_id,
                    RestaurantCategory.deletion_date.is_(None),
                )
            )
            if not category:
                raise _not_found()
        else:
            category = RestaurantCategory(id_proyect=self.project_id, created_by=self.user_id)
        slug = _slug(_required_text(payload, "slug", 30))
        if not slug:
            raise AppError("errors.invalid_field", 400, {"field": "slug"})
        duplicate = self.db.scalar(
            select(RestaurantCategory).where(
                RestaurantCategory.id_proyect == self.project_id,
                RestaurantCategory.slug == slug,
                RestaurantCategory.deletion_date.is_(None),
                RestaurantCategory.id_restaurant_category != (category_id or 0),
            )
        )
        if duplicate:
            raise AppError("restaurant.category_slug_taken", 409)
        category.slug = slug
        category.label = _required_text(payload, "label", 80)
        category.icon = str(payload.get("icon") or "plate")[:40]
        category.color = str(payload.get("color") or "").strip()[:20] or None
        category.sort_order = _integer(payload.get("sort_order", 100), "sort_order", minimum=0)
        category.is_active = bool(payload.get("is_active", True))
        if not category_id:
            self.db.add(category)
        self.db.flush()
        self._audit("category", "update" if category_id else "create", {
            "id_restaurant_category": category.id_restaurant_category, "slug": category.slug
        })
        return category.serialize()

    def list_orders(self, status: str | None = None, visit_id: int | None = None) -> list[dict]:
        query = _order_query(self.project_id).order_by(RestaurantOrder.started_at.desc())
        if status:
            query = query.where(RestaurantOrder.status == status)
        if visit_id:
            query = query.where(RestaurantOrder.id_restaurant_visit == visit_id)
        return [order.serialize() for order in self.db.scalars(query).unique().all()]

    def get_order(self, order_id: int) -> RestaurantOrder:
        order = self.db.scalar(
            _order_query(self.project_id).where(RestaurantOrder.id_restaurant_order == order_id)
        )
        if not order:
            raise _not_found()
        return order

    def add_order_item(self, order_id: int, payload: dict) -> dict:
        order = self.get_order(order_id)
        if order.status != "borrador":
            raise AppError("restaurant.order_not_editable", 409)
        dish_id = _integer(payload.get("id_restaurant_dish"), "id_restaurant_dish")
        dish = self.db.scalar(
            select(RestaurantDish).where(
                RestaurantDish.id_restaurant_dish == dish_id,
                RestaurantDish.id_proyect == self.project_id,
                RestaurantDish.is_active.is_(True),
                RestaurantDish.deletion_date.is_(None),
            )
        )
        if not dish:
            raise _not_found()
        guisado_1 = payload.get("id_guisado_1")
        if dish.requires_guisado and not guisado_1:
            raise AppError("restaurant.guisado_required", 400)
        for guisado_id in filter(None, (guisado_1, payload.get("id_guisado_2"))):
            if not self.db.scalar(
                select(RestaurantGuisado.id_restaurant_guisado).where(
                    RestaurantGuisado.id_restaurant_guisado == int(guisado_id),
                    RestaurantGuisado.id_proyect == self.project_id,
                    RestaurantGuisado.is_active.is_(True),
                )
            ):
                raise _not_found()
        item = RestaurantOrderItem(
            id_restaurant_order=order_id,
            id_restaurant_dish=dish_id,
            quantity=_integer(payload.get("quantity", 1), "quantity"),
            unit_price=dish.price,
            note=str(payload.get("note") or "").strip()[:255] or None,
            id_guisado_1=guisado_1,
            id_guisado_2=payload.get("id_guisado_2"),
            combinado=bool(payload.get("combinado", False)),
            created_by=self.user_id,
        )
        self.db.add(item)
        self.db.flush()
        self.db.expire(order, ["items"])
        return self.get_order(order_id).serialize()

    def remove_order_item(self, order_id: int, item_id: int) -> dict:
        order = self.get_order(order_id)
        if order.status != "borrador":
            raise AppError("restaurant.order_not_editable", 409)
        item = self.db.scalar(
            select(RestaurantOrderItem).where(
                RestaurantOrderItem.id_restaurant_order_item == item_id,
                RestaurantOrderItem.id_restaurant_order == order_id,
                RestaurantOrderItem.deletion_date.is_(None),
            )
        )
        if not item:
            raise _not_found()
        self.db.delete(item)
        self.db.flush()
        self.db.expire(order, ["items"])
        return self.get_order(order_id).serialize()

    def advance_order(self, order_id: int, new_status: str) -> dict:
        order = self.get_order(order_id)
        expected = ORDER_TRANSITIONS.get(order.status)
        if new_status != expected:
            raise AppError(
                "restaurant.invalid_status_transition",
                409,
                {"current": order.status, "expected": expected},
            )
        if new_status == "pedido" and not order.items:
            raise AppError("restaurant.empty_order", 400)
        now = datetime.utcnow()
        order.status = new_status
        timestamp_fields = {
            "pedido": "sent_at",
            "en_preparacion": "cooked_at",
            "listo_para_entrega": "ready_at",
            "entregado": "delivered_at",
        }
        setattr(order, timestamp_fields[new_status], now)
        self.db.flush()
        return order.serialize()

    def _apply_tip(self, order: RestaurantOrder, payload: dict) -> None:
        tip_type = payload.get("tip_type", "manual")
        if tip_type == "porcentaje":
            percent = _decimal(payload.get("tip_percent", 0), "tip_percent")
            order.tip_percent = percent
            order.tip_amount = (Decimal(str(order.subtotal)) * percent / Decimal("100")).quantize(
                Decimal("0.01")
            )
        else:
            order.tip_percent = None
            order.tip_amount = _decimal(payload.get("tip_amount", 0), "tip_amount").quantize(
                Decimal("0.01")
            )
        order.tip_type = tip_type

    def _payment_method(self, payload: dict) -> str:
        method = str(payload.get("payment_method") or "efectivo").strip()
        if method not in PAYMENT_METHODS:
            raise AppError("errors.invalid_field", 400, {"field": "payment_method"})
        return method

    def _require_open_register(self, method: str) -> None:
        """Exige turno de caja abierto para cobrar en efectivo.

        Sin esto el efectivo entra sin quedar dentro de ningun turno: el
        corte solo suma lo cobrado desde que se abrio la caja, asi que ese
        dinero no aparece en ningun arqueo y el faltante se descubre hasta
        contar el cajon. Tarjeta y transferencia no pasan por el cajon, asi
        que no se bloquean.
        """
        if method in ("tarjeta", "transferencia"):
            return
        if not self.current_cash_session():
            raise AppError("restaurant.register_not_open", 409)

    def pay_order(self, order_id: int, payload: dict) -> dict:
        """Cobra una sola cuenta (un comensal)."""
        order = self.get_order(order_id)
        if order.status != "entregado":
            raise AppError("restaurant.order_not_delivered", 409)
        method = self._payment_method(payload)
        self._require_open_register(method)
        self._apply_tip(order, payload)
        total = Decimal(str(order.total))
        cash_due = self._settle(order, method, total, payload)
        received = payload.get("received_amount")
        if received is not None:
            received = _decimal(received, "received_amount").quantize(Decimal("0.01"))
            if received < cash_due:
                raise AppError("restaurant.insufficient_payment", 409, {
                    "due": float(cash_due), "received": float(received)
                })
            order.received_amount = received
        order.status = "pagado"
        order.paid_at = datetime.utcnow()
        self.db.flush()
        avisos = self._consume_inventory([order])
        data = order.serialize()
        data["inventory_warnings"] = avisos
        return data

    def _settle(
        self, order: RestaurantOrder, method: str, total: Decimal, payload: dict
    ) -> Decimal:
        """Fija la forma de pago del renglon y devuelve cuanto entra en efectivo."""
        order.payment_method = method
        order.received_amount = None
        order.cash_amount = None
        if method == "efectivo":
            return total
        if method == "mixto":
            cash = _decimal(payload.get("cash_amount"), "cash_amount").quantize(Decimal("0.01"))
            if cash > total:
                raise AppError("errors.invalid_field", 400, {"field": "cash_amount"})
            order.cash_amount = cash
            return cash
        return Decimal("0")

    def pay_visit(self, visit_id: int, payload: dict) -> dict:
        """Cobra de una sola vez todas las cuentas entregadas de una visita.

        Es el cobro "todo junto": el cliente paga la mesa completa. La
        propina y el efectivo capturados aplican al total de la visita y se
        reparten entre las cuentas con `_split_exact`, para que los reportes
        por cuenta sigan cuadrando contra el total cobrado.
        """
        visit = self._visit(visit_id)
        orders = [order for order in visit.orders if order.status == "entregado"]
        if not orders:
            raise AppError("restaurant.no_payable_orders", 409)
        method = self._payment_method(payload)
        self._require_open_register(method)

        subtotal = sum(Decimal(str(order.subtotal)) for order in orders)
        tip_type = payload.get("tip_type", "manual")
        if tip_type == "porcentaje":
            percent = _decimal(payload.get("tip_percent", 0), "tip_percent")
            tip_total = (subtotal * percent / Decimal("100")).quantize(Decimal("0.01"))
        else:
            percent = None
            tip_total = _decimal(payload.get("tip_amount", 0), "tip_amount").quantize(
                Decimal("0.01")
            )
        weights = [Decimal(str(order.subtotal)) for order in orders]
        for order, tip_part in zip(orders, _split_exact(tip_total, weights)):
            order.tip_type = tip_type
            order.tip_percent = percent
            order.tip_amount = tip_part

        total = sum(Decimal(str(order.total)) for order in orders)
        if method == "mixto":
            cash_total = _decimal(payload.get("cash_amount"), "cash_amount").quantize(
                Decimal("0.01")
            )
            if cash_total > total:
                raise AppError("errors.invalid_field", 400, {"field": "cash_amount"})
        elif method == "efectivo":
            cash_total = total
        else:
            cash_total = Decimal("0")

        received = payload.get("received_amount")
        if received is not None:
            received = _decimal(received, "received_amount").quantize(Decimal("0.01"))
            if received < cash_total:
                raise AppError("restaurant.insufficient_payment", 409, {
                    "due": float(cash_total), "received": float(received)
                })

        # El efectivo se reparte llenando cuenta por cuenta en vez de a
        # prorrata: asi la suma de las partes es exacta sin arrastrar
        # centavos de redondeo.
        remaining_cash = cash_total
        remaining_received = received if received is not None else None
        now = datetime.utcnow()
        for order in orders:
            order_total = Decimal(str(order.total))
            order.payment_method = method
            order.cash_amount = None
            order.received_amount = None
            if method == "mixto":
                part = min(order_total, remaining_cash)
                order.cash_amount = part
                remaining_cash -= part
            if remaining_received is not None:
                part = min(order_total, remaining_received)
                order.received_amount = part
                remaining_received -= part
            order.status = "pagado"
            order.paid_at = now
        self.db.flush()
        avisos = self._consume_inventory(orders)
        return {
            "visit": self.get_visit(visit_id),
            "inventory_warnings": avisos,
            "paid_orders": len(orders),
            "total": float(total),
            "tip_total": float(tip_total),
            "cash_total": float(cash_total),
            "received_amount": float(received) if received is not None else None,
            "change_amount": float(received - cash_total) if received is not None else 0.0,
        }

    def kitchen_board(self) -> list[dict]:
        orders = []
        for status in ("pedido", "en_preparacion", "listo_para_entrega"):
            orders.extend(self.list_orders(status=status))
        return sorted(orders, key=lambda order: order["started_at"] or "")

    def kpis(self) -> dict:
        paid = self.db.scalars(
            _order_query(self.project_id).where(RestaurantOrder.status == ESTADO_DE_VENTA)
        ).unique().all()
        total_sales = sum(order.subtotal for order in paid)
        tips = sum(float(order.tip_amount or 0) for order in paid)
        dish_totals: dict[str, int] = {}
        table_totals: dict[int, int] = {}
        delivery_minutes = []
        for order in paid:
            if order.visit and order.visit.table:
                table_totals[order.visit.table.number] = table_totals.get(order.visit.table.number, 0) + 1
            for item in order.items:
                title = item.dish.title if item.dish else "Sin platillo"
                dish_totals[title] = dish_totals.get(title, 0) + item.quantity
            if order.ready_at and order.delivered_at:
                delivery_minutes.append((order.delivered_at - order.ready_at).total_seconds() / 60)
        active_tables = self.db.scalar(
            select(func.count(RestaurantVisit.id_restaurant_visit)).where(
                RestaurantVisit.id_proyect == self.project_id,
                RestaurantVisit.status == "active",
                RestaurantVisit.deletion_date.is_(None),
            )
        )
        return {
            "total_sales": round(total_sales, 2),
            "tips": round(tips, 2),
            "avg_ticket": round(total_sales / len(paid), 2) if paid else 0,
            "avg_minutes_from_ready_to_delivered": round(
                sum(delivery_minutes) / len(delivery_minutes), 2
            )
            if delivery_minutes
            else 0,
            "active_tables": int(active_tables or 0),
            "top_dishes": [
                {"dish": name, "quantity": quantity}
                for name, quantity in sorted(dish_totals.items(), key=lambda item: item[1], reverse=True)[:5]
            ],
            "top_tables": [
                {"table": number, "services": services}
                for number, services in sorted(table_totals.items(), key=lambda item: item[1], reverse=True)[:5]
            ],
        }

    def sales_report(self, start: str | None, end: str | None) -> dict:
        orders = self.db.scalars(
            _order_query(self.project_id).where(RestaurantOrder.status == ESTADO_DE_VENTA)
        ).unique().all()
        start_date = date.fromisoformat(start) if start else None
        end_date = date.fromisoformat(end) if end else None
        filtered = [
            order
            for order in orders
            if order.paid_at
            and (not start_date or order.paid_at.date() >= start_date)
            and (not end_date or order.paid_at.date() <= end_date)
        ]
        by_day: dict[str, dict] = {}
        for order in filtered:
            key = order.paid_at.date().isoformat()
            bucket = by_day.setdefault(key, {"date": key, "orders": 0, "sales": 0.0, "tips": 0.0})
            bucket["orders"] += 1
            bucket["sales"] += order.subtotal
            bucket["tips"] += float(order.tip_amount or 0)
        days = [by_day[key] for key in sorted(by_day)]
        for day in days:
            day["sales"] = round(day["sales"], 2)
            day["tips"] = round(day["tips"], 2)
        return {
            "days": days,
            "total_orders": len(filtered),
            "total_sales": round(sum(day["sales"] for day in days), 2),
            "total_tips": round(sum(day["tips"] for day in days), 2),
        }

    def current_cash_session(self) -> RestaurantCashSession | None:
        return self.db.scalar(
            select(RestaurantCashSession)
            .where(
                RestaurantCashSession.id_proyect == self.project_id,
                RestaurantCashSession.status == "open",
                RestaurantCashSession.deletion_date.is_(None),
            )
            .order_by(RestaurantCashSession.opened_at.desc())
        )

    def cash_history(self) -> list[dict]:
        sessions = self.db.scalars(
            select(RestaurantCashSession)
            .where(
                RestaurantCashSession.id_proyect == self.project_id,
                RestaurantCashSession.deletion_date.is_(None),
            )
            .order_by(RestaurantCashSession.opened_at.desc())
            .limit(30)
        ).all()
        return [session.serialize() for session in sessions]

    def open_cash_session(self, payload: dict) -> dict:
        if self.current_cash_session():
            raise AppError("restaurant.register_already_open", 409)
        session = RestaurantCashSession(
            id_proyect=self.project_id,
            opened_by_id=self.user_id,
            opening_amount=_decimal(payload.get("opening_amount", 0), "opening_amount"),
            status="open",
            created_by=self.user_id,
        )
        self.db.add(session)
        self.db.flush()
        return session.serialize()

    def close_cash_session(self, payload: dict) -> dict:
        session = self.current_cash_session()
        if not session:
            raise AppError("restaurant.register_not_open", 409)
        paid = self.db.scalars(
            _order_query(self.project_id).where(
                RestaurantOrder.status == ESTADO_DE_VENTA, RestaurantOrder.paid_at >= session.opened_at
            )
        ).unique().all()
        # Solo el efectivo debe cuadrar contra el cajon. Antes se sumaba
        # order.total de TODO lo cobrado, asi que cada pago con tarjeta o
        # transferencia inflaba el esperado y el arqueo salia con faltante
        # por ese mismo monto.
        cash_sales = sum(order.cash_portion for order in paid)
        session.expected_amount = Decimal(
            str(float(session.opening_amount) + cash_sales)
        ).quantize(Decimal("0.01"))
        session.closing_amount = _decimal(payload.get("closing_amount"), "closing_amount").quantize(
            Decimal("0.01")
        )
        session.difference = session.closing_amount - session.expected_amount
        session.notes = str(payload.get("notes") or "").strip()[:255] or None
        session.closed_by_id = self.user_id
        session.closed_at = datetime.utcnow()
        session.status = "closed"
        self.db.flush()
        return session.serialize()

    def list_waiters(self) -> list[dict]:
        return [
            waiter.serialize()
            for waiter in self.db.scalars(
                select(RestaurantWaiter)
                .where(
                    RestaurantWaiter.id_proyect == self.project_id,
                    RestaurantWaiter.deletion_date.is_(None),
                )
                .order_by(RestaurantWaiter.name)
            ).all()
        ]

    def save_waiter(self, payload: dict, waiter_id: int | None = None) -> dict:
        waiter = self._waiter(waiter_id) if waiter_id else RestaurantWaiter(
            id_proyect=self.project_id, created_by=self.user_id
        )
        waiter.name = _required_text(payload, "name", 120)
        waiter.nickname = _required_text(payload, "nickname", 80)
        waiter.status = str(payload.get("status") or "active")[:30]
        waiter.max_tables = _integer(payload.get("max_tables", 15), "max_tables")
        waiter.id_user = payload.get("id_user") or None
        if not waiter_id:
            self.db.add(waiter)
        self.db.flush()
        return waiter.serialize()

    def list_admin_catalogs(self) -> dict:
        return {
            **self.list_menu(),
            "tables": self.list_tables(),
            "waiters": self.list_waiters(),
            "reservations": self.list_reservations(),
            "inventory": self.list_inventory(),
            "inventory_summary": self.inventory_summary(),
            "recipes": self.list_recipes(),
            # El calculo ya existia para la caja; el panel de administracion
            # tambien lo necesita y no habia razon para duplicarlo.
            "kpis": self.kpis(),
        }

    def save_table(self, payload: dict, table_id: int | None = None) -> dict:
        table = self._table(table_id) if table_id else RestaurantTable(
            id_proyect=self.project_id, created_by=self.user_id
        )
        table.number = _integer(payload.get("number"), "number")
        table.capacity = _integer(payload.get("capacity", 4), "capacity")
        table.location_description = str(payload.get("location_description") or "").strip()[:160] or None
        table.is_active = bool(payload.get("is_active", True))
        if not table_id:
            self.db.add(table)
        self.db.flush()
        self._audit("table", "update" if table_id else "create", {
            "id_restaurant_table": table.id_restaurant_table, "number": table.number
        })
        return table.serialize()

    def save_dish(self, payload: dict, dish_id: int | None = None) -> dict:
        category = str(payload.get("category") or "")
        if category not in self._allowed_categories():
            raise AppError("errors.invalid_field", 400, {"field": "category"})
        dish = self._dish(dish_id) if dish_id else RestaurantDish(
            id_proyect=self.project_id, created_by=self.user_id
        )
        dish.title = _required_text(payload, "title", 140)
        dish.description = str(payload.get("description") or "").strip() or None
        dish.icon = str(payload.get("icon") or "plate")[:40]
        dish.category = category
        dish.price = _decimal(payload.get("price"), "price")
        dish.production_cost = _decimal(payload.get("production_cost", 0), "production_cost")
        dish.requires_guisado = bool(payload.get("requires_guisado", False))
        dish.schedule = str(payload.get("schedule") or "all")[:10]
        dish.is_active = bool(payload.get("is_active", True))
        if not dish_id:
            self.db.add(dish)
        self.db.flush()
        self._audit("dish", "update" if dish_id else "create", {
            "id_restaurant_dish": dish.id_restaurant_dish, "title": dish.title
        })
        return dish.serialize()

    def save_guisado(self, payload: dict) -> dict:
        guisado = RestaurantGuisado(
            id_proyect=self.project_id,
            name=_required_text(payload, "name", 120),
            is_active=True,
            created_by=self.user_id,
        )
        self.db.add(guisado)
        self.db.flush()
        self._audit("guisado", "create", {
            "id_restaurant_guisado": guisado.id_restaurant_guisado, "name": guisado.name
        })
        return guisado.serialize()

    def soft_delete_catalog_item(self, kind: str, record_id: int) -> None:
        mapping = {
            "dish": (RestaurantDish, RestaurantDish.id_restaurant_dish),
            "guisado": (RestaurantGuisado, RestaurantGuisado.id_restaurant_guisado),
            "table": (RestaurantTable, RestaurantTable.id_restaurant_table),
            "waiter": (RestaurantWaiter, RestaurantWaiter.id_restaurant_waiter),
            "category": (RestaurantCategory, RestaurantCategory.id_restaurant_category),
        }
        if kind not in mapping:
            raise _not_found()
        model, primary_key = mapping[kind]
        record = self.db.scalar(
            select(model).where(
                primary_key == record_id,
                model.id_proyect == self.project_id,
                model.deletion_date.is_(None),
            )
        )
        if not record:
            raise _not_found()
        record.deletion_date = datetime.utcnow()
        if hasattr(record, "is_active"):
            record.is_active = False
        self._audit(kind, "delete", {"record_id": record_id})

    def list_reservations(self) -> list[dict]:
        return [
            item.serialize()
            for item in self.db.scalars(
                select(RestaurantReservation)
                .where(
                    RestaurantReservation.id_proyect == self.project_id,
                    RestaurantReservation.deletion_date.is_(None),
                )
                .order_by(
                    RestaurantReservation.reservation_date.desc(),
                    RestaurantReservation.reservation_time.desc(),
                )
            ).all()
        ]

    def save_reservation(self, payload: dict) -> dict:
        try:
            reservation_date = date.fromisoformat(str(payload.get("reservation_date")))
            reservation_time = datetime.strptime(str(payload.get("reservation_time")), "%H:%M").time()
        except ValueError as exc:
            raise AppError("errors.invalid_field", 400, {"field": "reservation_date"}) from exc
        reservation = RestaurantReservation(
            id_proyect=self.project_id,
            id_restaurant_table=payload.get("id_restaurant_table") or None,
            name=_required_text(payload, "name", 140),
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            guests=_integer(payload.get("guests"), "guests"),
            status=str(payload.get("status") or "pending")[:40],
            event_type=str(payload.get("event_type") or "").strip()[:80] or None,
            created_by=self.user_id,
        )
        self.db.add(reservation)
        self.db.flush()
        return reservation.serialize()

    def list_inventory(self) -> list[dict]:
        return [
            item.serialize()
            for item in self.db.scalars(
                select(RestaurantInventoryItem)
                .where(
                    RestaurantInventoryItem.id_proyect == self.project_id,
                    RestaurantInventoryItem.deletion_date.is_(None),
                )
                .order_by(RestaurantInventoryItem.description)
            ).all()
        ]

    def save_inventory_item(self, payload: dict) -> dict:
        item = RestaurantInventoryItem(
            id_proyect=self.project_id,
            description=_required_text(payload, "description", 160),
            quantity=_decimal(payload.get("quantity", 0), "quantity"),
            unit=_required_text(payload, "unit", 40),
            cost_per_unit=_decimal(payload.get("cost_per_unit", 0), "cost_per_unit"),
            created_by=self.user_id,
        )
        self.db.add(item)
        self.db.flush()
        self._audit("inventory_item", "create", {
            "id_restaurant_inventory_item": item.id_restaurant_inventory_item,
            "description": item.description,
        })
        return item.serialize()

    def _inventory_item(self, item_id: int) -> RestaurantInventoryItem:
        item = self.db.scalar(
            select(RestaurantInventoryItem).where(
                RestaurantInventoryItem.id_restaurant_inventory_item == item_id,
                RestaurantInventoryItem.id_proyect == self.project_id,
                RestaurantInventoryItem.deletion_date.is_(None),
            )
        )
        if not item:
            raise _not_found()
        return item

    def list_inventory_movements(self, item_id: int | None = None, limit: int = 200) -> list[dict]:
        query = (
            select(RestaurantInventoryMovement)
            .where(
                RestaurantInventoryMovement.id_proyect == self.project_id,
                RestaurantInventoryMovement.deletion_date.is_(None),
            )
            .options(selectinload(RestaurantInventoryMovement.item))
        )
        if item_id:
            query = query.where(
                RestaurantInventoryMovement.id_restaurant_inventory_item
                == _integer(item_id, "id_restaurant_inventory_item")
            )
        rows = self.db.scalars(
            query.order_by(RestaurantInventoryMovement.creation_date.desc())
            .limit(max(1, min(int(limit or 200), 1000)))
        ).all()
        return [row.serialize() for row in rows]

    def create_inventory_movement(self, payload: dict) -> dict:
        """Registra un movimiento y deja el saldo del insumo consistente.

        'ajuste' fija el saldo al valor capturado (conteo fisico); los demas
        lo suman o restan. Un movimiento que dejaria el saldo en negativo se
        rechaza: es un error de captura, no un sobregiro valido.
        """
        movement_type = str(payload.get("movement_type") or "").strip()
        if movement_type not in INVENTORY_MOVEMENT_TYPES:
            raise AppError("errors.invalid_field", 400, {"field": "movement_type"})
        item = self._inventory_item(
            _integer(payload.get("id_restaurant_inventory_item"), "id_restaurant_inventory_item")
        )
        # minimum=0 permite capturar un ajuste a cero (merma total, conteo en
        # blanco); los otros tipos igual quedan validados por el saldo final.
        quantity = _decimal(payload.get("quantity"), "quantity", minimum=Decimal("0"))
        previous = Decimal(str(item.quantity or 0))
        if movement_type == "ajuste":
            new_quantity = quantity
        elif movement_type == "entrada":
            new_quantity = previous + quantity
        else:  # salida, merma
            new_quantity = previous - quantity
        if new_quantity < 0:
            raise AppError("restaurant.inventory_insufficient", 409, {
                "available": float(previous), "requested": float(quantity)
            })
        movement = RestaurantInventoryMovement(
            id_proyect=self.project_id,
            id_restaurant_inventory_item=item.id_restaurant_inventory_item,
            movement_type=movement_type,
            quantity=quantity,
            previous_quantity=previous,
            new_quantity=new_quantity,
            unit_cost=(
                _decimal(payload["unit_cost"], "unit_cost")
                if payload.get("unit_cost") is not None
                else None
            ),
            reason=str(payload.get("reason") or "").strip()[:255] or None,
            created_by=self.user_id,
        )
        item.quantity = new_quantity
        self.db.add(movement)
        self.db.flush()

        # Y el mismo movimiento en el libro del nucleo, si el insumo esta
        # enlazado a un producto. Un solo inventario para todos los proyectos:
        # ver `restaurant_inventory_bridge`. Si el reflejo falla, el movimiento
        # del restaurante NO se deshace -- el consumo ya ocurrio -- y el fallo
        # sale en la respuesta.
        sin_reflejar = self._puente_de_inventario()(
            self.db, item, movement, self._usuario())

        self._audit("inventory_movement", movement_type, {
            "id_restaurant_inventory_item": item.id_restaurant_inventory_item,
            "quantity": float(quantity),
            "previous_quantity": float(previous),
            "new_quantity": float(new_quantity),
        })
        salida = movement.serialize()
        if sin_reflejar:
            salida["core_inventory_warning"] = sin_reflejar
        return salida

    def _consume_inventory(self, orders: list[RestaurantOrder]) -> list[dict]:
        """Descuenta del inventario los insumos de lo que se acaba de cobrar.

        Reglas, en orden de importancia:

        1. **Nunca bloquea el cobro.** El platillo ya se preparo y se
           entrego; negarse a cobrar porque el sistema cree que no hay
           cebolla es peor que un saldo inexacto. Si no alcanza, se descuenta
           hasta cero y el faltante se reporta.
        2. **No descuenta si las unidades no coinciden.** La receta guarda su
           unidad como texto libre y no hay tabla de conversion: descontar
           150 "g" de un saldo en "kg" seria un error de tres ordenes de
           magnitud. Se omite y se avisa.
        3. **Un movimiento por insumo**, no uno por renglon de la orden: se
           agrega primero el consumo para que el kardex quede legible.

        Devuelve la lista de avisos para que la caja los pueda mostrar.
        """
        # Consumo agregado por insumo, con las recetas involucradas.
        consumo: dict[int, Decimal] = {}
        avisos: list[dict] = []
        platillos_sin_receta: set[str] = set()

        for order in orders:
            for item in order.items:
                recetas = self.db.scalars(
                    select(RestaurantRecipeItem).where(
                        RestaurantRecipeItem.id_restaurant_dish == item.id_restaurant_dish,
                        RestaurantRecipeItem.id_proyect == self.project_id,
                        RestaurantRecipeItem.deletion_date.is_(None),
                    )
                ).all()
                if not recetas:
                    platillos_sin_receta.add(item.dish.title if item.dish else str(item.id_restaurant_dish))
                    continue
                for receta in recetas:
                    cantidad = Decimal(str(receta.quantity)) * Decimal(int(item.quantity or 0))
                    consumo[receta.id_restaurant_inventory_item] = (
                        consumo.get(receta.id_restaurant_inventory_item, Decimal("0")) + cantidad
                    )

        if platillos_sin_receta:
            avisos.append({
                "code": "sin_receta",
                "dishes": sorted(platillos_sin_receta),
            })

        # Unidades de las recetas por insumo, para comparar contra el insumo.
        for inventory_id, cantidad in consumo.items():
            item = self.db.scalar(
                select(RestaurantInventoryItem).where(
                    RestaurantInventoryItem.id_restaurant_inventory_item == inventory_id,
                    RestaurantInventoryItem.id_proyect == self.project_id,
                    RestaurantInventoryItem.deletion_date.is_(None),
                )
            )
            if not item:
                continue
            unidades_receta = {
                (u or "").strip().lower()
                for u in self.db.scalars(
                    select(RestaurantRecipeItem.unit).where(
                        RestaurantRecipeItem.id_restaurant_inventory_item == inventory_id,
                        RestaurantRecipeItem.id_proyect == self.project_id,
                        RestaurantRecipeItem.deletion_date.is_(None),
                    )
                ).all()
            }
            unidad_insumo = (item.unit or "").strip().lower()
            if unidades_receta - {unidad_insumo}:
                avisos.append({
                    "code": "unidad_distinta",
                    "item": item.description,
                    "item_unit": item.unit,
                    "recipe_units": sorted(unidades_receta),
                })
                continue

            previo = Decimal(str(item.quantity or 0))
            descontado = min(cantidad, previo) if previo > 0 else Decimal("0")
            faltante = cantidad - descontado
            if faltante > 0:
                avisos.append({
                    "code": "existencias_insuficientes",
                    "item": item.description,
                    "required": float(cantidad),
                    "available": float(previo),
                    "short": float(faltante),
                })
            if descontado <= 0:
                continue
            nuevo = previo - descontado
            razon = "Consumo por venta"
            if faltante > 0:
                razon += f" (faltaron {faltante} {item.unit})"
            renglon = RestaurantInventoryMovement(
                id_proyect=self.project_id,
                id_restaurant_inventory_item=inventory_id,
                movement_type="salida",
                quantity=descontado,
                previous_quantity=previo,
                new_quantity=nuevo,
                reason=razon[:255],
                created_by=self.user_id,
            )
            self.db.add(renglon)
            item.quantity = nuevo
            # Hace falta el identificador del renglon para la llave de
            # idempotencia del reflejo, asi que se vuelca antes de reflejar.
            self.db.flush()
            fallo = self._puente_de_inventario()(
                self.db, item, renglon, self._usuario())
            if fallo:
                avisos.append({"code": "nucleo_no_reflejado", **fallo})

        if consumo or avisos:
            self._audit("inventory_consumption", "salida", {
                "orders": [o.id_restaurant_order for o in orders],
                "items_affected": len(consumo),
                "warnings": [a["code"] for a in avisos],
            })
        self.db.flush()
        return avisos

    def inventory_summary(self) -> dict:
        """Valor del inventario y insumos agotados, para el panel de admin."""
        items = self.db.scalars(
            select(RestaurantInventoryItem).where(
                RestaurantInventoryItem.id_proyect == self.project_id,
                RestaurantInventoryItem.deletion_date.is_(None),
            )
        ).all()
        total_value = sum(
            Decimal(str(item.quantity or 0)) * Decimal(str(item.cost_per_unit or 0))
            for item in items
        )
        return {
            "items_count": len(items),
            "total_value": float(round(total_value, 2)),
            "out_of_stock": [
                item.serialize() for item in items if Decimal(str(item.quantity or 0)) <= 0
            ],
        }

    def list_recipes(self) -> list[dict]:
        return [
            item.serialize()
            for item in self.db.scalars(
                select(RestaurantRecipeItem)
                .where(
                    RestaurantRecipeItem.id_proyect == self.project_id,
                    RestaurantRecipeItem.deletion_date.is_(None),
                )
                .order_by(RestaurantRecipeItem.id_restaurant_dish)
            ).all()
        ]

    def save_recipe_item(self, payload: dict) -> dict:
        dish_id = _integer(payload.get("id_restaurant_dish"), "id_restaurant_dish")
        inventory_id = _integer(
            payload.get("id_restaurant_inventory_item"), "id_restaurant_inventory_item"
        )
        if not self.db.scalar(
            select(RestaurantDish.id_restaurant_dish).where(
                RestaurantDish.id_restaurant_dish == dish_id,
                RestaurantDish.id_proyect == self.project_id,
            )
        ) or not self.db.scalar(
            select(RestaurantInventoryItem.id_restaurant_inventory_item).where(
                RestaurantInventoryItem.id_restaurant_inventory_item == inventory_id,
                RestaurantInventoryItem.id_proyect == self.project_id,
            )
        ):
            raise _not_found()
        # La unidad de la receta debe ser la misma del insumo: no hay tabla
        # de conversion, asi que una receta en "g" contra un saldo en "kg"
        # descontaria mil veces de mas al cobrar. Se exige que coincidan en
        # el alta para no generar ese dato.
        unidad = _required_text(payload, "unit", 40)
        unidad_insumo = self.db.scalar(
            select(RestaurantInventoryItem.unit).where(
                RestaurantInventoryItem.id_restaurant_inventory_item == inventory_id
            )
        )
        if (unidad or "").strip().lower() != (unidad_insumo or "").strip().lower():
            raise AppError("restaurant.recipe_unit_mismatch", 400, {
                "field": "unit", "expected": unidad_insumo
            })
        item = RestaurantRecipeItem(
            id_proyect=self.project_id,
            id_restaurant_dish=dish_id,
            id_restaurant_inventory_item=inventory_id,
            quantity=_decimal(payload.get("quantity"), "quantity", Decimal("0.001")),
            unit=unidad,
            created_by=self.user_id,
        )
        self.db.add(item)
        self.db.flush()
        return item.serialize()

    def _visit(self, visit_id: int) -> RestaurantVisit:
        visit = self.db.scalar(
            select(RestaurantVisit)
            .where(
                RestaurantVisit.id_restaurant_visit == visit_id,
                RestaurantVisit.id_proyect == self.project_id,
                RestaurantVisit.deletion_date.is_(None),
            )
            .options(selectinload(RestaurantVisit.orders).selectinload(RestaurantOrder.items))
        )
        if not visit:
            raise _not_found()
        return visit

    def _waiter(self, waiter_id: int | None) -> RestaurantWaiter:
        waiter = self.db.scalar(
            select(RestaurantWaiter).where(
                RestaurantWaiter.id_restaurant_waiter == waiter_id,
                RestaurantWaiter.id_proyect == self.project_id,
                RestaurantWaiter.deletion_date.is_(None),
            )
        )
        if not waiter:
            raise _not_found()
        return waiter

    def _table(self, table_id: int | None) -> RestaurantTable:
        table = self.db.scalar(
            select(RestaurantTable).where(
                RestaurantTable.id_restaurant_table == table_id,
                RestaurantTable.id_proyect == self.project_id,
                RestaurantTable.deletion_date.is_(None),
            )
        )
        if not table:
            raise _not_found()
        return table

    def _dish(self, dish_id: int | None) -> RestaurantDish:
        dish = self.db.scalar(
            select(RestaurantDish).where(
                RestaurantDish.id_restaurant_dish == dish_id,
                RestaurantDish.id_proyect == self.project_id,
                RestaurantDish.deletion_date.is_(None),
            )
        )
        if not dish:
            raise _not_found()
        return dish