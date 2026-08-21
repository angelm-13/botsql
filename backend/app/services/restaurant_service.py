from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.restaurant import (
    RestaurantCashSession,
    RestaurantDish,
    RestaurantGuisado,
    RestaurantInventoryItem,
    RestaurantOrder,
    RestaurantOrderItem,
    RestaurantRecipeItem,
    RestaurantReservation,
    RestaurantTable,
    RestaurantVisit,
    RestaurantWaiter,
)
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
            "categories": sorted(DISH_CATEGORIES),
        }

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

    def pay_order(self, order_id: int, payload: dict) -> dict:
        order = self.get_order(order_id)
        if order.status != "entregado":
            raise AppError("restaurant.order_not_delivered", 409)
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
        order.status = "pagado"
        order.paid_at = datetime.utcnow()
        self.db.flush()
        return order.serialize()

    def kitchen_board(self) -> list[dict]:
        orders = []
        for status in ("pedido", "en_preparacion", "listo_para_entrega"):
            orders.extend(self.list_orders(status=status))
        return sorted(orders, key=lambda order: order["started_at"] or "")

    def kpis(self) -> dict:
        paid = self.db.scalars(
            _order_query(self.project_id).where(RestaurantOrder.status == "pagado")
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
            _order_query(self.project_id).where(RestaurantOrder.status == "pagado")
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
                RestaurantOrder.status == "pagado", RestaurantOrder.paid_at >= session.opened_at
            )
        ).unique().all()
        sales = sum(order.total for order in paid)
        session.expected_amount = Decimal(str(float(session.opening_amount) + sales)).quantize(
            Decimal("0.01")
        )
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
            "recipes": self.list_recipes(),
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
        return table.serialize()

    def save_dish(self, payload: dict, dish_id: int | None = None) -> dict:
        category = str(payload.get("category") or "")
        if category not in DISH_CATEGORIES:
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
        return guisado.serialize()

    def soft_delete_catalog_item(self, kind: str, record_id: int) -> None:
        mapping = {
            "dish": (RestaurantDish, RestaurantDish.id_restaurant_dish),
            "guisado": (RestaurantGuisado, RestaurantGuisado.id_restaurant_guisado),
            "table": (RestaurantTable, RestaurantTable.id_restaurant_table),
            "waiter": (RestaurantWaiter, RestaurantWaiter.id_restaurant_waiter),
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
        return item.serialize()

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
        item = RestaurantRecipeItem(
            id_proyect=self.project_id,
            id_restaurant_dish=dish_id,
            id_restaurant_inventory_item=inventory_id,
            quantity=_decimal(payload.get("quantity"), "quantity", Decimal("0.001")),
            unit=_required_text(payload, "unit", 40),
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