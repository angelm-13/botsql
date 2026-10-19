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
from tests.test_api.test_api_purchase_order import ALMACEN_1, GERENTE, GERENTE_1, PROYECTO_B
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

    # --- material parcial: arrancar con lo que llego, completar con todo --------

    def _con_control(self, *, segunda_necesidad=True):
        """PROYECTO_B lo lidera el gerente de la prueba. Con `segunda_necesidad`,
        queda una que nunca entra en la orden."""
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_B).leader = GERENTE_1
            if segunda_necesidad:
                db.add(self._necesidad(9001, PROYECTO_B, "Varilla", 3, "pza", "buy"))

    def _recibir_el_cemento(self):
        id_orden = self._comprada()
        linea = next(l for l in self._leer(id_orden)["lines"] if l["id_proyect"] == PROYECTO_B)
        self.assertEqual(200, self._recibir(id_orden, [
            {"id_purchase_order_line": linea["id_purchase_order_line"],
             "quantity": linea["quantity"]}]).status_code)

    def _cerrar_tareas(self):
        with transaction_context() as db:
            db.query(Task).filter(Task.id_proyect == PROYECTO_B).update({"task_status": "terminada"})

    def test_a_project_starts_with_what_arrived_and_records_what_is_missing(self):
        from app.models.proyect_event import ProyectEvent

        self._con_control()
        self._en_espera_con_tarea()
        with self.assertRaises(AppError) as e:  # nada ha llegado: pide el motivo de siempre
            self._arrancar()
        self.assertEqual("errors.project_material_pending", e.exception.message_key)

        self._recibir_el_cemento()
        self.assertEqual({"total": 2, "received": 1, "on_order": 0, "not_ordered": 1,
                          "ready": False}, self._estado())
        self.assertEqual("in_progress", self._arrancar()["proyect_status"])  # sin motivo
        with transaction_context() as db:
            evento = db.query(ProyectEvent).filter(
                ProyectEvent.id_proyect == PROYECTO_B, ProyectEvent.new_status == "in_progress").one()
            self.assertEqual("Arranca con material parcial: 1 de 2 recibido", evento.reason)

    def test_a_project_cannot_be_completed_until_the_rest_arrives(self):
        from app.models import ProyectMaterialNeed

        self._con_control()
        self._en_espera_con_tarea()
        self._recibir_el_cemento()
        self._arrancar()
        self._cerrar_tareas()
        with self.assertRaises(AppError) as e:
            transition_project(PROYECTO_B, {"status": "completed"}, self.gerente_datos)
        self.assertEqual("errors.project_material_incomplete", e.exception.message_key)
        self.assertEqual(409, e.exception.status_code)

        with transaction_context() as db:  # lo que ya no aplica se cancela
            db.query(ProyectMaterialNeed).filter(ProyectMaterialNeed.id_proyect_material_need == 9001
                                                 ).update({"need_status": "cancelled"})
        self.assertEqual("completed", transition_project(
            PROYECTO_B, {"status": "completed"}, self.gerente_datos)["proyect_status"])

    def test_a_project_without_material_needs_completes_freely(self):
        with transaction_context() as db:
            from app.models import ProyectMaterialNeed
            db.query(ProyectMaterialNeed).filter(
                ProyectMaterialNeed.id_proyect == PROYECTO_B).delete()
            db.get(Proyect, PROYECTO_B).leader = GERENTE_1
        self._en_espera_con_tarea()
        self._arrancar()
        self._cerrar_tareas()
        self.assertEqual("completed", transition_project(
            PROYECTO_B, {"status": "completed"}, self.gerente_datos)["proyect_status"])

    def test_the_list_shows_how_much_material_is_missing(self):
        from app.services.project_management_service import list_projects

        self._con_control()
        self._en_espera_con_tarea()
        self._recibir_el_cemento()
        fila = next(p for p in list_projects(self.gerente_datos, per_page=100)["items"]
                    if p["id_proyect"] == PROYECTO_B)
        self.assertEqual(1, fila["material_readiness"]["received"])
        self.assertEqual(2, fila["material_readiness"]["total"])

    def _avisos_de_material_completo(self):
        from app.models import Notification

        with transaction_context() as db:
            return sorted(n.id_user_recipient for n in db.query(Notification).filter(
                Notification.id_proyect == PROYECTO_B, Notification.title == "Material completo"))

    def test_the_project_is_told_once_when_all_its_material_has_arrived(self):
        from app.services.project_management_service import avisar_material_completo

        self._con_control(segunda_necesidad=False)
        self._en_espera_con_tarea()
        self.assertEqual([], self._avisos_de_material_completo())

        self._recibir_el_cemento()  # era lo unico que pidio
        self.assertEqual([GERENTE_1], self._avisos_de_material_completo())
        avisar_material_completo({PROYECTO_B}, ALMACEN_1)  # otra recepcion de la misma orden
        self.assertEqual([GERENTE_1], self._avisos_de_material_completo())

    def test_no_notice_while_some_material_is_still_missing(self):
        self._con_control()
        self._en_espera_con_tarea()
        self._recibir_el_cemento()
        self.assertEqual([], self._avisos_de_material_completo())

    def test_a_project_that_has_not_reached_the_wait_gets_no_material_notice(self):
        """Autorizado todavia no se abastece: no hay aviso aunque llegue todo."""
        self._con_control(segunda_necesidad=False)
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_B).proyect_status = "authorized"
        self._recibir_el_cemento()
        self.assertEqual([], self._avisos_de_material_completo())

    def test_a_project_with_a_live_purchase_order_cannot_be_denied(self):
        id_orden = self._comprada()
        id_proyecto = next(l["id_proyect"] for l in self._leer(id_orden)["lines"]
                           if l.get("id_proyect"))
        with transaction_context() as db:  # solo un proyecto bloqueado puede negarse
            db.get(Proyect, id_proyecto).proyect_status = "blocked"
        with self.assertRaises(AppError) as e:
            transition_project(id_proyecto, {"status": "denied", "reason": "No procede"},
                               self.gerente_datos)
        self.assertEqual("errors.project_open_orders", e.exception.message_key)

    def test_the_public_api_default_rate_limit_reads_the_environment(self):
        import os
        from app.routes.public_catalog import _default_public_api_rate_limit

        os.environ["PUBLIC_API_RATE_LIMIT_DEFAULT"] = "7"
        try:
            self.assertEqual(7, _default_public_api_rate_limit())
        finally:
            del os.environ["PUBLIC_API_RATE_LIMIT_DEFAULT"]

    def test_a_cancelled_project_cannot_be_bought_for(self):
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_B).management_status = "cancelado"
        respuesta = self._crear()  # incluye una necesidad del proyecto cancelado
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_not_open", self._error(respuesta))
