"""El puente con el punto de venta.

Un solo inicio de sesion: el usuario entra en TYAKXA y el nucleo habla con el POS
por detras con una cuenta de servicio. Eso concentra poder en un sitio, asi que
lo que estas pruebas cuidan es que el puente no se convierta en una puerta
abierta al POS entero:

* solo se reenvia lo declarado; cualquier otra ruta no existe;
* cada ruta exige su capacidad, y la de caja no alcanza la administracion;
* el patron mas especifico gana, para que una ruta de cajero no quede tapada
  por una de administracion que empieza igual.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models import EntityPermission
from app.models.session import transaction_context
from app.services import pos_gateway
from tests.conftest import BackendTestCase


CAJERO = {"id_user": 5, "id_proyect": 1, "id_permission": 30}
ADMIN_POS = {"id_user": 6, "id_proyect": 1, "id_permission": 31}
AJENO = {"id_user": 7, "id_proyect": 1, "id_permission": 32}


class TestQueSeDejaPasar(unittest.TestCase):
    """La lista de rutas reenviables, sin tocar la base ni la red."""

    def test_an_undeclared_route_is_not_forwarded(self):
        """Un proxy que pasa todo entrega el POS entero."""
        self.assertIsNone(pos_gateway.capacidad_para("GET", "users"))
        self.assertIsNone(pos_gateway.capacidad_para("DELETE", "products"))
        self.assertIsNone(pos_gateway.capacidad_para("GET", "../../etc/passwd"))

    def test_the_till_routes_belong_to_the_cashier(self):
        for metodo, ruta in (
            ("POST", "checkout"),
            ("GET", "products"),
            ("GET", "sales/open"),
            ("POST", "cash/sessions/open"),
        ):
            with self.subTest(ruta=f"{metodo} {ruta}"):
                self.assertEqual("pos_terminal", pos_gateway.capacidad_para(metodo, ruta))

    def test_configuration_and_reports_need_the_admin_capability(self):
        for metodo, ruta in (
            ("POST", "products"),
            ("GET", "reports/sales-summary"),
            ("GET", "dashboard/sales-summary"),
            ("GET", "audit"),
        ):
            with self.subTest(ruta=f"{metodo} {ruta}"):
                self.assertEqual("pos_admin", pos_gateway.capacidad_para(metodo, ruta))

    def test_the_screens_added_later_have_their_route_declared(self):
        """Cada pantalla nueva necesita su ruta en la lista blanca.

        Sin esto la pantalla se ve pero llega vacia con un 404 del puente, que
        es peor que no tenerla: parece que el POS no tiene datos.
        """
        for metodo, ruta, capacidad in (
            # Catalogo y almacen: los ve quien cobra.
            ("GET", "products/low-stock", "pos_terminal"),
            ("GET", "products/units", "pos_terminal"),
            # El cajero lee la lista de clientes porque la necesita al cobrar;
            # la ficha con su credito y su historial ya es de administracion.
            ("GET", "customers", "pos_terminal"),
            ("GET", "customers/abc-123", "pos_admin"),
            ("POST", "customers", "pos_admin"),
            ("GET", "suppliers", "pos_admin"),
            ("GET", "promotions", "pos_admin"),
            ("GET", "expenses/categories", "pos_admin"),
            # Las cifras del tablero.
            ("GET", "dashboard/today-summary", "pos_admin"),
            ("GET", "dashboard/product-margin", "pos_admin"),
            ("GET", "dashboard/revenue-by-payment-method", "pos_admin"),
        ):
            with self.subTest(ruta=f"{metodo} {ruta}"):
                self.assertEqual(capacidad, pos_gateway.capacidad_para(metodo, ruta))

    def test_the_most_specific_pattern_wins(self):
        """`products/categories` es del cajero aunque `products/` sea de admin.

        Sin esta regla, el prefijo mas general tapa al mas concreto y un cajero
        se queda sin poder leer las categorias para cobrar.
        """
        self.assertEqual("pos_terminal",
                         pos_gateway.capacidad_para("GET", "products/categories"))
        self.assertEqual("pos_admin",
                         pos_gateway.capacidad_para("PUT", "products/abc-123"))

    def test_the_method_matters(self):
        """Leer productos es de caja; crearlos, de administracion."""
        self.assertEqual("pos_terminal", pos_gateway.capacidad_para("GET", "products"))
        self.assertEqual("pos_admin", pos_gateway.capacidad_para("POST", "products"))


class TestLaPuerta(BackendTestCase):
    """El comportamiento sobre HTTP, con permisos reales."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=30, entity_name="pos_terminal",
                                 control_type=7, created_by=1),
                EntityPermission(id_permission=31, entity_name="pos_admin",
                                 control_type=15, created_by=1),
                EntityPermission(id_permission=31, entity_name="pos_terminal",
                                 control_type=7, created_by=1),
            ])
        pos_gateway.reiniciar_sesion()

    def cabeceras(self, actor):
        import jwt
        from app.utils.auth import SECRET_KEY

        return {"Authorization": "Bearer " + jwt.encode(actor, SECRET_KEY, algorithm="HS256")}

    def test_the_link_list_is_readable_by_the_cashier(self):
        """El catalogo necesita esta lista para marcar quien descuenta y quien no.

        Si la pantalla no la pudiera leer tendria que suponer, y suponer aqui es
        decirle al operador que su venta descuenta del almacen cuando no lo hace.
        """
        respuesta = self.client.get("/pos/links", headers=self.cabeceras(CAJERO))
        self.assertEqual(200, respuesta.status_code)
        self.assertIn("items", respuesta.get_json())

    def test_declaring_a_link_is_reserved_to_the_administrator(self):
        """Enlazar decide de que producto del almacen sale cada venta.

        Es una decision de inventario, no de mostrador: si el cajero pudiera
        cambiarla, una venta podria empezar a descontar del producto equivocado
        sin que nadie lo autorizara.
        """
        respuesta = self.client.post(
            "/pos/links",
            json={"id_product": 1, "pos_product_id": "abc", "id_location": 1},
            headers=self.cabeceras(CAJERO),
        )
        self.assertEqual(403, respuesta.status_code)

    def test_someone_outside_the_point_of_sale_does_not_even_see_the_links(self):
        respuesta = self.client.get("/pos/links", headers=self.cabeceras(AJENO))
        self.assertEqual(403, respuesta.status_code)

    def test_a_route_that_is_not_forwardable_looks_absent(self):
        """404 y no 403: describir el POS a quien no lo alcanza es de mas."""
        respuesta = self.client.get("/pos/api/users", headers=self.cabeceras(ADMIN_POS))

        self.assertEqual(404, respuesta.status_code)

    def test_the_cashier_cannot_reach_the_administration(self):
        respuesta = self.client.get("/pos/api/reports/sales-summary",
                                    headers=self.cabeceras(CAJERO))

        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("pos_admin", self.json(respuesta)["meta"]["capability"])

    def test_someone_without_the_capability_reaches_nothing(self):
        respuesta = self.client.get("/pos/api/products", headers=self.cabeceras(AJENO))

        self.assertEqual(403, respuesta.status_code)

    def test_the_cashier_reaches_the_till_and_the_request_is_forwarded(self):
        # Se parchea donde se usa y no donde se define: la ruta importa la
        # funcion directamente, asi que cambiar el atributo del modulo original
        # no altera la referencia que la ruta ya tiene.
        from app.routes import pos_proxy

        with patch.object(pos_proxy, "reenviar", return_value=({"items": []}, 200)) as puente:
            respuesta = self.client.get("/pos/api/products",
                                        headers=self.cabeceras(CAJERO))

        self.assertEqual(200, respuesta.status_code)
        puente.assert_called_once()
        self.assertEqual(CAJERO["id_user"], puente.call_args.kwargs["actor"],
                         "el actor real de TYAKXA viaja al POS")

    def test_the_pos_answer_is_returned_as_it_came(self):
        """El usuario ve lo que el POS dijo, no un mensaje generico del puente."""
        from app.routes import pos_proxy

        with patch.object(pos_proxy, "reenviar",
                          return_value=({"error": "Sin existencia"}, 409)):
            respuesta = self.client.post("/pos/api/checkout",
                                         headers=self.cabeceras(CAJERO), json={})

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("Sin existencia", self.json(respuesta)["error"])


class TestLaSesionDeServicio(unittest.TestCase):
    def setUp(self):
        pos_gateway.reiniciar_sesion()

    def tearDown(self):
        pos_gateway.reiniciar_sesion()

    def test_without_credentials_it_says_so_instead_of_failing_obscurely(self):
        from app.utils.errors import AppError

        import os
        previos = {k: os.environ.pop(k, None) for k in ("POS_SERVICE_USER", "POS_SERVICE_PASSWORD")}
        try:
            with self.assertRaises(AppError) as raised:
                pos_gateway.reenviar("GET", "products", actor=1)
            self.assertEqual("errors.pos_gateway_not_configured", raised.exception.message_key)
        finally:
            for clave, valor in previos.items():
                if valor is not None:
                    os.environ[clave] = valor

    def test_the_status_endpoint_reports_a_missing_configuration(self):
        import os

        previos = {k: os.environ.pop(k, None) for k in ("POS_SERVICE_USER", "POS_SERVICE_PASSWORD")}
        try:
            informe = pos_gateway.estado()
            self.assertFalse(informe["configured"])
            self.assertIn("POS_SERVICE_USER", informe["detail"])
        finally:
            for clave, valor in previos.items():
                if valor is not None:
                    os.environ[clave] = valor


if __name__ == "__main__":
    unittest.main()
