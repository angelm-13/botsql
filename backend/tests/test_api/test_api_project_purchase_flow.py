"""El proyecto de punta a punta contra sus ordenes de compra.

Recorre lo que pasa con el material de un proyecto -sin pedir, en orden, recibido en
parte, recibido, orden cancelada- y que el candado de arranque del proyecto lo lea bien.
"""
from __future__ import annotations

from app.models import EntityPermission, Proyect, Task
from app.models.session import transaction_context
from app.services.project_management_service import (
    material_readiness, transition_project,
)
from app.utils.errors import AppError
from tests.test_api.test_api_purchase_order import GERENTE, GERENTE_1, PROYECTO_B
from tests.test_api.test_api_purchase_receive import BaseRecepcion


class TestProyectoContraOrdenes(BaseRecepcion):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=GERENTE, entity_name="project_authorization",
                                    scope_read=4, scope_update=4, created_by=1))
        self.gerente_datos = {"id_user": GERENTE_1, "id_permission": GERENTE}

    def _estado(self, proyecto=PROYECTO_B):
        with transaction_context() as db:
            return material_readiness(db, proyecto)

    def _en_espera_con_tarea(self, proyecto=PROYECTO_B):
        with transaction_context() as db:
            db.get(Proyect, proyecto).proyect_status = "authorized"
            db.add(Task(id_proyect=proyecto, task_description="T", task_status="pendiente",
                        owner=GERENTE_1, validation=GERENTE_1, dependency=0, created_by=1))
        transition_project(proyecto, {"status": "waiting_material"}, self.gerente_datos)

    def _arrancar(self, **extra):
        return transition_project(PROYECTO_B, {"status": "in_progress", **extra}, self.gerente_datos)

    def test_material_goes_from_not_ordered_to_received(self):
        self.assertEqual({"total": 1, "received": 0, "on_order": 0, "not_ordered": 1,
                          "ready": False}, self._estado())

        id_orden = self._comprada()  # surte tambien al proyecto B (cemento)
        self.assertEqual(1, self._estado()["on_order"])

        linea = next(l for l in self._leer(id_orden)["lines"] if l["id_proyect"] == PROYECTO_B)
        id_linea = linea["id_purchase_order_line"]
        self.assertEqual(200, self._recibir(id_orden, [
            {"id_purchase_order_line": id_linea, "quantity": linea["quantity"] - 1}]).status_code)
        self.assertEqual(1, self._estado()["on_order"])  # recibida en parte: aun no llega

        self.assertEqual(200, self._recibir(id_orden, [
            {"id_purchase_order_line": id_linea, "quantity": 1}]).status_code)
        self.assertEqual({"total": 1, "received": 1, "on_order": 0, "not_ordered": 0,
                          "ready": True}, self._estado())

    def test_a_cancelled_order_releases_the_need_back_to_not_ordered(self):
        id_orden = self._id(self._crear())
        self.assertEqual(1, self._estado()["on_order"])
        self.assertEqual(200, self._accion(id_orden, "cancel", note="Ya no se compra").status_code)
        self.assertEqual(1, self._estado()["not_ordered"])

    def test_start_is_blocked_until_the_material_arrives(self):
        self._en_espera_con_tarea()
        with self.assertRaises(AppError) as e:
            self._arrancar()
        self.assertEqual("errors.project_material_pending", e.exception.message_key)

        id_orden = self._comprada()
        with self.assertRaises(AppError):  # en camino todavia no es recibido
            self._arrancar()

        for l in self._leer(id_orden)["lines"]:
            self._recibir(id_orden, [{"id_purchase_order_line": l["id_purchase_order_line"],
                                      "quantity": l["quantity"]}])
        self.assertEqual("in_progress", self._arrancar()["proyect_status"])

    def test_a_blank_reason_does_not_unlock_the_start(self):
        self._en_espera_con_tarea()
        with self.assertRaises(AppError):
            self._arrancar(reason="   ")
        self.assertEqual("in_progress", self._arrancar(reason="Llega el lunes")["proyect_status"])

    def test_a_project_without_needs_starts_freely(self):
        with transaction_context() as db:
            from app.models import ProyectMaterialNeed
            db.query(ProyectMaterialNeed).filter(
                ProyectMaterialNeed.id_proyect == PROYECTO_B).delete()
        self._en_espera_con_tarea()
        self.assertTrue(self._estado()["ready"])
        self.assertEqual("in_progress", self._arrancar()["proyect_status"])
