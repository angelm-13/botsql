"""El presupuesto de compras por proyecto: lo fija gerencia y excederlo exige autorizacion."""
from __future__ import annotations

from tests.test_api.test_api_purchase_order import (
    BaseOrdenes, PROYECTO_A, PROYECTO_B,
)


class TestPresupuestoDeCompras(BaseOrdenes):
    # Las lineas de _renglones: 4,000 en el proyecto A y 6,000 en el B.

    def _fijar(self, id_proyecto, monto, headers=None, **extra):
        return self.client.put("/purchase-budgets/%s" % id_proyecto,
                               json={"amount": monto, **extra},
                               headers=headers or self._gerente())

    def test_purchasing_reads_budgets_but_only_the_manager_sets_them(self):
        self.assertEqual(403, self._fijar(PROYECTO_A, 5000, self._compras()).status_code)
        self.assertEqual(200, self.client.get(
            "/purchase-budgets", headers=self._compras()).status_code)
        self.assertEqual(200, self._fijar(PROYECTO_A, 5000).status_code)

    def test_invalid_amounts_are_refused_and_changes_leave_history(self):
        self.assertEqual(400, self._fijar(PROYECTO_A, -1).status_code)
        self.assertEqual(400, self._fijar(PROYECTO_A, "x").status_code)
        self.assertEqual(400, self._fijar(PROYECTO_A, 100, currency="EUR").status_code)
        self.assertEqual(404, self._fijar(9999, 100).status_code)
        self._fijar(PROYECTO_A, 5000)
        self._fijar(PROYECTO_A, 8000)
        items = self.json(self.client.get("/purchase-budgets/%s/history" % PROYECTO_A,
                                          headers=self._gerente()))["items"]
        self.assertEqual([(5000.0, 8000.0), (None, 5000.0)],
                         [(None if i["amount_before"] is None else float(i["amount_before"]),
                           float(i["amount_after"])) for i in items])

    def test_an_order_within_budget_follows_the_normal_policy(self):
        self._politica(authorize_above=20000)
        self._fijar(PROYECTO_A, 4000)
        self._fijar(PROYECTO_B, 6000)
        cuerpo = self.json(self._accion(self._id(self._crear()), "submit"))
        self.assertEqual("authorized", cuerpo["order_status"])
        self.assertFalse(cuerpo["exceeds_budget"])

    def test_exceeding_a_project_budget_needs_authorization_even_below_the_limit(self):
        self._politica(authorize_above=20000)
        self._fijar(PROYECTO_A, 3000)
        cuerpo = self.json(self._accion(self._id(self._crear()), "submit"))
        self.assertEqual("pending_authorization", cuerpo["order_status"])
        self.assertTrue(cuerpo["exceeds_budget"])
        fila = [b for b in cuerpo["budget"] if b["id_proyect"] == PROYECTO_A][0]
        self.assertEqual(1000.0, fila["over_by"])

    def test_it_is_released_only_with_a_note_and_not_by_its_author(self):
        self._politica(authorize_above=20000)
        self._fijar(PROYECTO_A, 3000)
        id_orden = self._id(self._crear(headers=self._gerente(1)))
        self._accion(id_orden, "submit", self._gerente(1))
        self.assertEqual(403, self._accion(id_orden, "authorize", self._gerente(1),
                                           note="va").status_code)
        sin_nota = self._accion(id_orden, "authorize", self._gerente(2))
        self.assertEqual(400, sin_nota.status_code)
        self.assertEqual("errors.budget_note_required", self._error(sin_nota))
        con_nota = self._accion(id_orden, "authorize", self._gerente(2), note="Se amplia")
        self.assertEqual("authorized", self.json(con_nota)["order_status"])

    def test_committed_orders_count_and_cancelled_ones_release_it(self):
        self._politica(authorize_above=20000)
        self._fijar(PROYECTO_A, 5000)
        primera = self._id(self._crear())
        self.assertFalse(self.json(self._accion(primera, "submit"))["exceeds_budget"])
        segunda = self._id(self._crear(lineas=[
            {"description": "Mas soldadura", "quantity": 1, "unit_cost": 2000,
             "id_proyect": PROYECTO_A}]))
        self.assertTrue(self.json(self._accion(segunda, "submit"))["exceeds_budget"])
        def fila():
            return [p for p in self.json(self.client.get(
                "/purchase-budgets", headers=self._gerente()))["items"]
                if p["id_proyect"] == PROYECTO_A][0]
        self.assertEqual(6000.0, fila()["committed"])
        self.assertTrue(fila()["exceeded"])
        self.assertEqual(200, self._accion(segunda, "cancel", note="ya no").status_code)
        self.assertEqual(4000.0, fila()["committed"])
        self.assertEqual(1000.0, fila()["available"])

    def test_a_project_without_budget_has_no_cap(self):
        self._politica(authorize_above=20000)
        cuerpo = self.json(self._accion(self._id(self._crear()), "submit"))
        self.assertEqual("authorized", cuerpo["order_status"])
        self.assertEqual([], cuerpo["budget"])
