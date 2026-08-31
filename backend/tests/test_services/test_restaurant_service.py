from decimal import Decimal

from app.models.restaurant import RestaurantDish, RestaurantTable
from app.models.session import transaction_context
from app.services.restaurant_service import RestaurantService
from tests.conftest import BackendTestCase


class TestRestaurantService(BackendTestCase):
    def test_complete_table_to_payment_flow(self):
        with transaction_context() as db:
            table = RestaurantTable(
                id_proyect=1, number=1, capacity=4, created_by=1
            )
            dish = RestaurantDish(
                id_proyect=1,
                title="Taco de guisado",
                category="taco",
                price=Decimal("18.00"),
                production_cost=Decimal("7.00"),
                created_by=1,
            )
            db.add_all([table, dish])
            db.flush()
            service = RestaurantService(db, 1, 1)
            visit = service.create_visit(
                {"id_restaurant_table": table.id_restaurant_table, "diners_count": 1}
            )
            order_id = visit["orders"][0]["id_restaurant_order"]
            order = service.add_order_item(
                order_id,
                {"id_restaurant_dish": dish.id_restaurant_dish, "quantity": 2},
            )
            assert order["subtotal"] == 36.0
            assert service.advance_order(order_id, "pedido")["status"] == "pedido"
            assert service.advance_order(order_id, "en_preparacion")["status"] == "en_preparacion"
            assert service.advance_order(order_id, "listo_para_entrega")["status"] == "listo_para_entrega"
            assert service.advance_order(order_id, "entregado")["status"] == "entregado"
            # Cobrar en efectivo exige turno de caja abierto: sin el, el dinero
            # entra fuera de todo arqueo y el faltante no aparece hasta contar
            # el cajon. La prueba se escribio antes de esa regla y cobraba sin
            # abrir caja, que es justo lo que ahora no se permite.
            service.open_cash_session({"opening_amount": 0})
            paid = service.pay_order(
                order_id, {"tip_type": "porcentaje", "tip_percent": 10}
            )
            assert paid["status"] == "pagado"
            assert paid["tip_amount"] == 3.6
            assert paid["total"] == 39.6