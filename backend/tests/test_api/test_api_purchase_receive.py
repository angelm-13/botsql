"""Recibir lo comprado, y los avisos de cada paso de la orden.

Lo que estas pruebas sostienen:

* la recepcion es del almacen -capacidad `purchase_receive`, no el permiso de escribir
  ordenes-; quien compro puede recibir si su rol la tiene (2026-10-19), no hay regla
  por persona;
* se recibe por renglon y en parcialidades: la orden queda `partially_received` hasta
  que llega todo, y recibir de mas se rechaza en vez de esconderse;
* a cada paso le toca avisar a quien sigue: autorizar, comprar, recibir.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models import EntityPermission, Notification, User
from app.models.session import transaction_context
from app.utils.errors import AppError
from tests.model_factory import build_model
from tests.test_api.test_api_purchase_order import (
    ALMACEN, ALMACEN_1, BaseOrdenes, COMPRAS, COMPRAS_1, GERENTE, GERENTE_1, GERENTE_2,
    PROYECTO_A, PROYECTO_B, _con_id,
)


class BaseRecepcion(BaseOrdenes):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # El almacen solo consulta las ordenes, pero recibe.
                EntityPermission(id_permission=ALMACEN, entity_name="purchase_receive",
                                 scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=GERENTE, entity_name="purchase_receive",
                                 scope_read=4, scope_update=4, created_by=1),
            ])
            # Los avisos buscan usuarios reales por permiso.
            for id_user, permiso in ((COMPRAS_1, COMPRAS), (GERENTE_1, GERENTE),
                                     (GERENTE_2, GERENTE), (ALMACEN_1, ALMACEN)):
                db.add(_con_id(build_model(User, username="u%d" % id_user, email="u%d@x.mx" % id_user,
                                           id_permission=permiso, user_type="user"),
                           id_user=id_user))

    # --- ayudas ---------------------------------------------------------------

    def _comprada(self):
        id_orden = self._orden_completa()
        self.assertEqual(200, self._comprar(id_orden).status_code)
        return id_orden

    def _renglon(self, id_orden, posicion=0):
        return self._leer(id_orden)["lines"][posicion]

    def _recibir(self, id_orden, lineas, headers=None, **extra):
        return self._accion(id_orden, "receive", headers or self._almacen(),
                            lines=lineas, **extra)

    def _avisos(self, id_user):
        with transaction_context() as db:
            return [(n.notification_type, n.target_entity, n.target_id)
                    for n in db.scalars(select(Notification).where(
                        Notification.id_user_recipient == id_user)
                        .order_by(Notification.id_notification))]


class TestRecibirLaCompra(BaseRecepcion):

    def test_the_warehouse_receives_everything_and_the_order_is_received(self):
        id_orden = self._comprada()
        lineas = self._leer(id_orden)["lines"]

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas])

        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        cuerpo = self.json(respuesta)
        self.assertEqual("received", cuerpo["order_status"])
        self.assertEqual([l["quantity"] for l in lineas],
                         [l["quantity_received"] for l in cuerpo["lines"]])
        self.assertIn("received", self._eventos(id_orden))

    def test_the_same_receipt_sent_twice_counts_once(self):
        id_orden = self._comprada()
        primero = self._renglon(id_orden)
        lineas = [{"id_purchase_order_line": primero["id_purchase_order_line"], "quantity": 2}]

        self.assertEqual(200, self._recibir(id_orden, lineas, idempotency_key="clic-1").status_code)
        repetida = self._recibir(id_orden, lineas, idempotency_key="clic-1")

        self.assertEqual(200, repetida.status_code)
        self.assertEqual(2, self._renglon(id_orden)["quantity_received"])
        self.assertEqual(200, self._recibir(id_orden, lineas, idempotency_key="clic-2").status_code)
        self.assertEqual(4, self._renglon(id_orden)["quantity_received"])

    def test_a_need_on_a_live_order_cannot_be_edited_or_returned(self):
        id_orden = self._comprada()
        id_need = next(l["id_proyect_material_need"] for l in self._leer(id_orden)["lines"]
                       if l.get("id_proyect_material_need"))

        from app.services.proyect_material_need_service import update_need

        with self.assertRaises(AppError) as caja:
            update_need(id_need, {"quantity": 99}, {"id_user": 1, "is_superuser": True})
        devolver = self.client.post("/material-needs/%s/return" % id_need,
                                    json={"note": "no se entiende"}, headers=self._compras())

        self.assertEqual("errors.need_already_in_order", caja.exception.message_key)
        self.assertEqual(409, devolver.status_code)

    def test_a_project_with_a_live_purchase_order_cannot_be_cancelled(self):
        from app.services.project_management_service import transition_management

        id_orden = self._comprada()
        id_proyecto = next(l["id_proyect"] for l in self._leer(id_orden)["lines"]
                           if l.get("id_proyect"))

        with self.assertRaises(AppError) as caja:
            transition_management(id_proyecto, {"management_status": "cancelado"},
                                  {"id_user": 1, "is_superuser": True})

        self.assertEqual("errors.project_open_orders", caja.exception.message_key)

    def test_what_already_arrived_stops_being_a_pending_purchase(self):
        id_orden = self._comprada()
        antes = {p["id_proyect_material_need"]
                 for g in self.json(self.client.get("/material-needs/to-buy",
                                                    headers=self._compras()))["items"]
                 for p in g["projects"] if p["order"]}
        self.assertTrue(antes)
        lineas = self._leer(id_orden)["lines"]

        self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas])

        despues = {p["id_proyect_material_need"]
                   for g in self.json(self.client.get("/material-needs/to-buy",
                                                      headers=self._compras()))["items"]
                   for p in g["projects"]}
        self.assertFalse(antes & despues)

    def test_a_partial_delivery_leaves_the_order_partially_received_until_the_rest_arrives(self):
        id_orden = self._comprada()
        primero, segundo = self._leer(id_orden)["lines"]

        parcial = self.json(self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"], "quantity": 4}]))
        self.assertEqual("partially_received", parcial["order_status"])
        self.assertEqual(4, parcial["lines"][0]["quantity_received"])

        # La segunda llamada SUMA a lo ya recibido.
        resto = self.json(self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"],
             "quantity": primero["quantity"] - 4},
            {"id_purchase_order_line": segundo["id_purchase_order_line"],
             "quantity": segundo["quantity"]}]))
        self.assertEqual("received", resto["order_status"])
        self.assertEqual(primero["quantity"], resto["lines"][0]["quantity_received"])

    def test_receiving_more_than_was_bought_is_refused_and_changes_nothing(self):
        id_orden = self._comprada()
        primero = self._renglon(id_orden)

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"],
             "quantity": primero["quantity"] + 1}])

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_receive_exceeds", self._error(respuesta))
        despues = self._leer(id_orden)
        self.assertEqual("purchased", despues["order_status"])
        self.assertEqual(0, despues["lines"][0]["quantity_received"])

    def test_one_bad_line_rolls_back_the_good_ones(self):
        id_orden = self._comprada()
        primero, segundo = self._leer(id_orden)["lines"]

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"], "quantity": 1},
            {"id_purchase_order_line": segundo["id_purchase_order_line"],
             "quantity": segundo["quantity"] + 1}])

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual(0, self._renglon(id_orden)["quantity_received"])

    def test_the_same_line_twice_in_one_reception_is_refused(self):
        id_orden = self._comprada()
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1},
            {"id_purchase_order_line": id_renglon, "quantity": 1}])

        self.assertEqual(409, respuesta.status_code)

    def test_a_line_from_another_order_is_not_found(self):
        id_orden = self._comprada()
        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": 999999, "quantity": 1}])
        self.assertEqual(404, respuesta.status_code)

    def test_a_reception_with_nothing_in_it_is_refused(self):
        id_orden = self._comprada()
        self.assertEqual(400, self._recibir(id_orden, []).status_code)

    def test_zero_or_negative_quantities_are_refused(self):
        id_orden = self._comprada()
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]
        for cantidad in (0, -3, "abc"):
            with self.subTest(cantidad=cantidad):
                respuesta = self._recibir(id_orden, [
                    {"id_purchase_order_line": id_renglon, "quantity": cantidad}])
                self.assertEqual(400, respuesta.status_code)

    def test_an_order_that_was_not_bought_cannot_be_received(self):
        id_orden = self._orden_completa()  # autorizada, con factura, sin comprar
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1}])

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_not_receivable", self._error(respuesta))

    def test_purchasing_cannot_receive_what_it_bought(self):
        """Compras no lleva la capacidad: ni recibe lo suyo ni lo ajeno."""
        id_orden = self._comprada()
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]

        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1}], self._compras())

        self.assertEqual(403, respuesta.status_code)

    def test_nobody_without_the_capability_receives(self):
        id_orden = self._comprada()
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]
        self.assertIn(self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1}], self._nadie()).status_code,
            (401, 403))

    def test_whoever_bought_can_receive_if_the_role_has_the_capability(self):
        """Quien recibe lo manda el Gestor, no la persona: el gerente que compro,
        y tiene la capacidad, tambien confirma que llego (pedido de Adser)."""
        self._politica(authorize_above=0, manager_buys_above=5000)
        id_orden = self._autorizada()
        self._factura(id_orden)
        self.assertEqual(200, self._comprar(id_orden, self._gerente(1)).status_code)
        id_renglon = self._renglon(id_orden)["id_purchase_order_line"]

        self.assertTrue(self._leer(id_orden, self._gerente(1))["actions"]["receive"])
        propia = self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1}], self._gerente(1))
        self.assertEqual(200, propia.status_code)

        ajena = self._recibir(id_orden, [
            {"id_purchase_order_line": id_renglon, "quantity": 1}], self._gerente(2))
        self.assertEqual(200, ajena.status_code)

    def test_only_the_warehouse_is_offered_the_receive_button_and_only_once_bought(self):
        id_orden = self._orden_completa()
        self.assertFalse(self._leer(id_orden, self._almacen())["actions"]["receive"])

        self._comprar(id_orden)
        self.assertTrue(self._leer(id_orden, self._almacen())["actions"]["receive"])
        self.assertFalse(self._leer(id_orden, self._compras())["actions"]["receive"])

    def test_once_received_there_is_nothing_left_to_receive(self):
        id_orden = self._comprada()
        lineas = self._leer(id_orden)["lines"]
        self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas])

        self.assertFalse(self._leer(id_orden, self._almacen())["actions"]["receive"])
        again = self._recibir(id_orden, [
            {"id_purchase_order_line": lineas[0]["id_purchase_order_line"], "quantity": 1}])
        self.assertEqual(409, again.status_code)

    def test_a_received_order_cannot_be_cancelled(self):
        id_orden = self._comprada()
        lineas = self._leer(id_orden)["lines"]
        self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas])
        self.assertEqual(409, self._accion(id_orden, "cancel", note="ya no la quiero").status_code)


class TestLosAvisosDeLaOrden(BaseRecepcion):

    def test_submitting_warns_everyone_who_can_authorize_but_not_the_sender(self):
        id_orden = self._por_autorizar()

        esperado = ("purchase_order_pending", "purchase_order", id_orden)
        self.assertIn(esperado, self._avisos(GERENTE_1))
        self.assertIn(esperado, self._avisos(GERENTE_2))
        self.assertEqual([], self._avisos(COMPRAS_1))
        self.assertEqual([], self._avisos(ALMACEN_1))

    def test_an_order_below_the_authorization_limit_warns_nobody(self):
        self._politica(authorize_above=20000)
        id_orden = self._id(self._crear())
        self._accion(id_orden, "submit")
        self.assertEqual([], self._avisos(GERENTE_1))

    def test_authorizing_warns_whoever_asked_for_the_order(self):
        id_orden = self._por_autorizar()
        self._accion(id_orden, "authorize", self._gerente(2))

        self.assertIn(("purchase_order_authorized", "purchase_order", id_orden),
                      self._avisos(COMPRAS_1))
        # Quien autorizo no se avisa a si mismo.
        self.assertNotIn("purchase_order_authorized",
                         [a[0] for a in self._avisos(GERENTE_2)])

    def test_rejecting_warns_the_requester(self):
        id_orden = self._por_autorizar()
        self._accion(id_orden, "reject", self._gerente(2), note="El monto no cuadra")

        self.assertIn(("purchase_order_rejected", "purchase_order", id_orden),
                      self._avisos(COMPRAS_1))

    def test_buying_warns_the_projects_waiting_for_the_material_and_not_the_whole_warehouse(self):
        """El rol Almacenista lo llevan decenas de personas: avisarles a todas es ruido."""
        id_orden = self._comprada()

        esperado = ("purchase_order_purchased", "purchase_order", id_orden)
        # Los lideres de los dos proyectos que esperan material (ids 11 y 12).
        self.assertIn(esperado, self._avisos(11))
        self.assertIn(esperado, self._avisos(12))
        self.assertEqual([], self._avisos(ALMACEN_1))

    def test_an_order_that_comes_back_for_a_new_authorization_warns_the_authorizers(self):
        self._politica(authorize_above=0, overrun=10)
        id_orden = self._autorizada()
        self._factura(id_orden, monto="20000.00")  # el doble de lo autorizado
        antes = len(self._avisos(GERENTE_1))

        respuesta = self._comprar(id_orden)

        self.assertTrue(self.json(respuesta)["reauthorization_required"])
        self.assertEqual(antes + 1, len(self._avisos(GERENTE_1)))
        self.assertEqual([], [a for a in self._avisos(GERENTE_2)
                              if a[0] == "purchase_order_purchased"])

    def test_receiving_warns_the_buyer_and_the_supervisors_of_the_projects(self):
        id_orden = self._comprada()
        lineas = self._leer(id_orden)["lines"]
        self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas])

        self.assertIn(("purchase_order_received", "purchase_order", id_orden),
                      self._avisos(COMPRAS_1))
        # Los lideres de los dos proyectos que reciben material (ids 11 y 12).
        self.assertIn(("purchase_order_received", "purchase_order", id_orden), self._avisos(11))
        self.assertIn(("purchase_order_received", "purchase_order", id_orden), self._avisos(12))
        # Quien recibio no se avisa a si mismo.
        self.assertNotIn("purchase_order_received", [a[0] for a in self._avisos(ALMACEN_1)])

    def test_a_partial_reception_says_so(self):
        id_orden = self._comprada()
        primero = self._renglon(id_orden)
        self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"], "quantity": 1}])

        self.assertIn(("purchase_order_partially_received", "purchase_order", id_orden),
                      self._avisos(COMPRAS_1))

    def test_a_failed_reception_warns_nobody(self):
        id_orden = self._comprada()
        primero = self._renglon(id_orden)
        self._recibir(id_orden, [
            {"id_purchase_order_line": primero["id_purchase_order_line"],
             "quantity": primero["quantity"] + 1}])

        self.assertEqual([], [a for a in self._avisos(COMPRAS_1)
                              if a[0].startswith("purchase_order_") and "received" in a[0]])


class TestElRegistroDeLaRecepcion(BaseRecepcion):

    def _rol(self, nombre):
        from app.modules import registry
        return next(r for r in registry.ROLES if r.nombre == nombre)

    def test_the_warehouse_and_the_manager_receive_and_purchasing_does_not(self):
        self.assertIn("purchase_receive", self._rol("Almacenista").capacidades)
        self.assertIn("purchase_receive", self._rol("Gerente").capacidades)
        self.assertNotIn("purchase_receive", self._rol("Compras").capacidades)

    def test_the_warehouse_still_cannot_write_orders(self):
        from app.modules import registry
        self.assertEqual(registry.CONSULTA, self._rol("Almacenista").modulos["compras"])
