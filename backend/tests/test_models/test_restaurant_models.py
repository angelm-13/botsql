from decimal import Decimal

from app.models.restaurant import RestaurantDish, RestaurantOrder, RestaurantOrderItem


def test_restaurant_order_totals_are_serialized_without_queries():
    dish = RestaurantDish(
        id_proyect=1,
        title="Taco",
        category="taco",
        price=Decimal("18.00"),
        production_cost=Decimal("7.00"),
        created_by=1,
    )
    order = RestaurantOrder(
        id_proyect=1,
        id_restaurant_visit=1,
        diner_index=1,
        tip_amount=Decimal("5.00"),
        created_by=1,
    )
    order.items = [
        RestaurantOrderItem(
            id_restaurant_dish=1,
            quantity=2,
            unit_price=Decimal("18.00"),
            dish=dish,
            created_by=1,
        )
    ]

    assert order.subtotal == 36.0
    assert order.total == 41.0
    assert order.serialize()["items"][0]["dish"]["title"] == "Taco"


def test_dish_schedule_supports_weekday_weekend_and_specific_days():
    dish = RestaurantDish(
        id_proyect=1,
        title="Pozole",
        category="platillo_dia",
        price=Decimal("80.00"),
        production_cost=Decimal("30.00"),
        schedule="weekend",
        created_by=1,
    )

    from datetime import date

    assert dish.is_available_today(date(2026, 8, 22)) is True
    assert dish.is_available_today(date(2026, 8, 20)) is False