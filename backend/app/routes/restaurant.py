from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.session import transaction_context
from app.services.restaurant_service import RestaurantService
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError


bp_restaurant = Blueprint("restaurant", __name__, url_prefix="/restaurant")


def _payload() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _actor(user_data: dict) -> tuple[int, int]:
    project_id = user_data.get("id_proyect") or user_data.get("project_id")
    user_id = user_data.get("id_user") or user_data.get("user_id")
    if not project_id or not user_id:
        raise AppError("errors.permission_denied", 403)
    return int(project_id), int(user_id)


def _execute(user_data: dict, operation):
    project_id, user_id = _actor(user_data)
    with transaction_context() as db:
        return operation(RestaurantService(db, project_id, user_id))


@bp_restaurant.get("/waiter/bootstrap")
@token_required
@require_entity_permission("restaurant_waiter", "read")
def waiter_bootstrap(user_data):
    return jsonify(
        _execute(
            user_data,
            lambda service: {
                "tables": service.list_tables(),
                "visits": service.list_visits("active"),
                "menu": service.list_menu(only_today=True),
                "delivery": service.kitchen_board(),
                "waiters": service.list_waiters(),
                "reservations": service.list_reservations(),
            },
        )
    )


@bp_restaurant.post("/waiter/visits")
@token_required
@require_entity_permission("restaurant_waiter", "create")
def create_visit(user_data):
    return jsonify(_execute(user_data, lambda service: service.create_visit(_payload()))), 201


@bp_restaurant.get("/waiter/visits/<int:visit_id>")
@token_required
@require_entity_permission("restaurant_waiter", "read")
def get_visit(user_data, visit_id: int):
    return jsonify(_execute(user_data, lambda service: service.get_visit(visit_id)))


@bp_restaurant.post("/waiter/visits/<int:visit_id>/diners")
@token_required
@require_entity_permission("restaurant_waiter", "create")
def add_diner(user_data, visit_id: int):
    return jsonify(_execute(user_data, lambda service: service.add_diner(visit_id))), 201


@bp_restaurant.delete("/waiter/visits/<int:visit_id>/diners/<int:diner_index>")
@token_required
@require_entity_permission("restaurant_waiter", "delete")
def remove_diner(user_data, visit_id: int, diner_index: int):
    return jsonify(
        _execute(user_data, lambda service: service.remove_diner(visit_id, diner_index))
    )


@bp_restaurant.post("/waiter/visits/<int:visit_id>/close")
@token_required
@require_entity_permission("restaurant_waiter", "update")
def close_visit(user_data, visit_id: int):
    return jsonify(_execute(user_data, lambda service: service.close_visit(visit_id)))


@bp_restaurant.post("/waiter/orders/<int:order_id>/items")
@token_required
@require_entity_permission("restaurant_waiter", "create")
def add_order_item(user_data, order_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.add_order_item(order_id, _payload()))
    ), 201


@bp_restaurant.delete("/waiter/orders/<int:order_id>/items/<int:item_id>")
@token_required
@require_entity_permission("restaurant_waiter", "delete")
def remove_order_item(user_data, order_id: int, item_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.remove_order_item(order_id, item_id))
    )


@bp_restaurant.post("/waiter/orders/<int:order_id>/send")
@token_required
@require_entity_permission("restaurant_waiter", "update")
def send_order(user_data, order_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.advance_order(order_id, "pedido"))
    )


@bp_restaurant.post("/waiter/orders/<int:order_id>/deliver")
@token_required
@require_entity_permission("restaurant_waiter", "update")
def deliver_order(user_data, order_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.advance_order(order_id, "entregado"))
    )


@bp_restaurant.post("/waiter/reservations")
@token_required
@require_entity_permission("restaurant_waiter", "create")
def create_reservation(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.save_reservation(_payload()))
    ), 201


@bp_restaurant.get("/kitchen/board")
@token_required
@require_entity_permission("restaurant_kitchen", "read")
def kitchen_board(user_data):
    return jsonify({"items": _execute(user_data, lambda service: service.kitchen_board())})


@bp_restaurant.patch("/kitchen/orders/<int:order_id>/status")
@token_required
@require_entity_permission("restaurant_kitchen", "update")
def kitchen_status(user_data, order_id: int):
    status = str(_payload().get("status") or "")
    if status not in {"en_preparacion", "listo_para_entrega"}:
        raise AppError("errors.invalid_field", 400, {"field": "status"})
    return jsonify(
        _execute(user_data, lambda service: service.advance_order(order_id, status))
    )


@bp_restaurant.get("/cashier/bootstrap")
@token_required
@require_entity_permission("restaurant_cashier", "read")
def cashier_bootstrap(user_data):
    def load(service):
        current = service.current_cash_session()
        return {
            "kpis": service.kpis(),
            "pending_payments": service.list_orders(status="entregado"),
            "current_register": current.serialize() if current else None,
            "register_history": service.cash_history(),
        }

    return jsonify(_execute(user_data, load))


@bp_restaurant.get("/cashier/reports")
@token_required
@require_entity_permission("restaurant_cashier", "read")
def cashier_reports(user_data):
    return jsonify(
        _execute(
            user_data,
            lambda service: service.sales_report(request.args.get("start"), request.args.get("end")),
        )
    )


@bp_restaurant.post("/cashier/orders/<int:order_id>/pay")
@token_required
@require_entity_permission("restaurant_cashier", "update")
def pay_order(user_data, order_id: int):
    return jsonify(_execute(user_data, lambda service: service.pay_order(order_id, _payload())))


@bp_restaurant.post("/cashier/register/open")
@token_required
@require_entity_permission("restaurant_cashier", "create")
def open_register(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.open_cash_session(_payload()))
    ), 201


@bp_restaurant.post("/cashier/register/close")
@token_required
@require_entity_permission("restaurant_cashier", "update")
def close_register(user_data):
    return jsonify(_execute(user_data, lambda service: service.close_cash_session(_payload())))


@bp_restaurant.get("/admin/bootstrap")
@token_required
@require_entity_permission("restaurant_admin", "read")
def admin_bootstrap(user_data):
    return jsonify(_execute(user_data, lambda service: service.list_admin_catalogs()))


@bp_restaurant.post("/admin/dishes")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_dish(user_data):
    return jsonify(_execute(user_data, lambda service: service.save_dish(_payload()))), 201


@bp_restaurant.put("/admin/dishes/<int:dish_id>")
@token_required
@require_entity_permission("restaurant_admin", "update")
def update_dish(user_data, dish_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.save_dish(_payload(), dish_id))
    )


@bp_restaurant.post("/admin/guisados")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_guisado(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.save_guisado(_payload()))
    ), 201


@bp_restaurant.post("/admin/tables")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_table(user_data):
    return jsonify(_execute(user_data, lambda service: service.save_table(_payload()))), 201


@bp_restaurant.put("/admin/tables/<int:table_id>")
@token_required
@require_entity_permission("restaurant_admin", "update")
def update_table(user_data, table_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.save_table(_payload(), table_id))
    )


@bp_restaurant.post("/admin/waiters")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_waiter(user_data):
    return jsonify(_execute(user_data, lambda service: service.save_waiter(_payload()))), 201


@bp_restaurant.put("/admin/waiters/<int:waiter_id>")
@token_required
@require_entity_permission("restaurant_admin", "update")
def update_waiter(user_data, waiter_id: int):
    return jsonify(
        _execute(user_data, lambda service: service.save_waiter(_payload(), waiter_id))
    )


@bp_restaurant.delete("/admin/<string:kind>/<int:record_id>")
@token_required
@require_entity_permission("restaurant_admin", "delete")
def delete_catalog_item(user_data, kind: str, record_id: int):
    _execute(user_data, lambda service: service.soft_delete_catalog_item(kind, record_id))
    return jsonify({"deleted": True})


@bp_restaurant.post("/admin/reservations")
@token_required
@require_entity_permission("restaurant_admin", "create")
def admin_create_reservation(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.save_reservation(_payload()))
    ), 201


@bp_restaurant.post("/admin/inventory")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_inventory_item(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.save_inventory_item(_payload()))
    ), 201


@bp_restaurant.post("/admin/recipes")
@token_required
@require_entity_permission("restaurant_admin", "create")
def create_recipe_item(user_data):
    return jsonify(
        _execute(user_data, lambda service: service.save_recipe_item(_payload()))
    ), 201
