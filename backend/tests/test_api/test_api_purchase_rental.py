"""Renta de maquinaria: de la lista del proyecto a la devolucion al proveedor.

Lo que estas pruebas sostienen:

* la obra pide la renta en su lista, con el periodo; nace confirmada (no se revisa
  contra el almacen) y la misma maquina en otro periodo es otra renta;
* Compras la cubre con una orden: tarifa por dia/semana/mes y el costo del renglon
  sale de tarifa x periodos, asi el total, el presupuesto y la autorizacion no cambian;
* la maquinaria no se recibe en el almacen: "Llego a obra" y "Devuelta" los marca quien
  lleva la obra o quien recibe compras; nadie mas;
* la prorroga la decide quien autoriza compras, y no la suya;
* un proyecto no se completa con maquinaria sin devolver;
* el aviso de vencimiento sale una vez por etapa (vence pronto, vencida).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.models import Notification, Proyect, ProyectMaterialNeed, PurchaseOrderLine
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.tiempo import hoy_negocio
from tests.test_api.test_api_purchase_order import (
    COMPRAS_1, PROYECTO_A, SUPERVISOR, USUARIO_SUPERVISOR, _con_id,
)
from tests.test_api.test_api_purchase_receive import BaseRecepcion

N_PLATAFORMA = 50
ADMIN = {"id_user": 1, "is_superuser": True}


class BaseRentas(BaseRecepcion):
    def setUp(self):
        super().setUp()
        self.inicio = hoy_negocio()
        self.fin = self.inicio + timedelta(days=2)  # 3 dias contando inicio y fin
        with transaction_context() as db:
            db.add(_con_id(ProyectMaterialNeed(
                id_proyect=PROYECTO_A, description="Plataforma de tijera 10 m", unit="equipo",
                quantity=1, need_status="open", review_result="buy", need_kind="rental",
                rental_start=self.inicio, rental_end=self.fin, created_by=11),
                id_proyect_material_need=N_PLATAFORMA))

    def _lider(self):
        """El supervisor que lidera la obra A (leader = 11)."""
        return self._h(USUARIO_SUPERVISOR, SUPERVISOR)

    def _orden_de_renta(self, tarifa=1500, unidad="day"):
        """Comprada: autorizada, con su factura por el total, y comprada."""
        id_orden = self._autorizada(lineas=[{
            "id_proyect_material_need": N_PLATAFORMA, "rental_rate": tarifa,
            "rental_rate_unit": unidad}])
        total = self._leer(id_orden)["quoted_total"]
        self._factura(id_orden, monto="%.2f" % total)
        self.assertEqual(200, self._comprar(id_orden).status_code)
        return id_orden

    def _linea(self, id_orden):
        return self._leer(id_orden)["lines"][0]

    def _renta(self, id_linea, accion, headers=None, **cuerpo):
        return self.client.post("/purchase-order-lines/%s/rental/%s" % (id_linea, accion),
                                json=cuerpo, headers=headers or self._lider())

    def _en_obra(self):
        id_orden = self._orden_de_renta()
        id_linea = self._linea(id_orden)["id_purchase_order_line"]
        respuesta = self._renta(id_linea, "arrive")
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return id_orden, id_linea


class TestPedirLaRenta(BaseRentas):

    def test_a_rental_is_asked_with_its_period_and_is_born_confirmed(self):
        from app.services.proyect_material_need_service import create_need

        fila = create_need(PROYECTO_A, {
            "need_kind": "rental", "description": "Retroexcavadora", "quantity": 1,
            "rental_start": self.inicio.isoformat(),
            "rental_end": (self.inicio + timedelta(days=6)).isoformat()}, ADMIN)

        self.assertEqual("rental", fila["need_kind"])
        self.assertEqual("buy", fila["review_result"])
        self.assertFalse(fila["needs_review"])

    def test_machinery_is_counted_in_its_own_units_not_in_pieces(self):
        from app.services.proyect_material_need_service import create_need

        base = {"need_kind": "rental", "description": "Grua de 30 toneladas", "quantity": 1,
                "rental_start": self.inicio.isoformat(),
                "rental_end": (self.inicio + timedelta(days=1)).isoformat()}
        self.assertEqual("equipo", create_need(PROYECTO_A, {**base, "unit": "Equipo"}, ADMIN)["unit"])
        with self.assertRaises(AppError) as caja:
            create_need(PROYECTO_A, {**base, "description": "Pipa de agua", "unit": "pza"}, ADMIN)
        self.assertEqual(["equipo", "unidad", "servicio", "viaje"],
                         caja.exception.meta["allowed"])
        # Y el material no acepta las de la maquinaria.
        with self.assertRaises(AppError):
            create_need(PROYECTO_A, {"description": "Soldadura 6013", "quantity": 1,
                                     "unit": "viaje"}, ADMIN)

    def test_a_rental_without_a_valid_period_is_refused(self):
        from app.services.proyect_material_need_service import create_need

        base = {"need_kind": "rental", "description": "Retroexcavadora", "quantity": 1}
        casos = (
            ({}, "errors.invalid_field"),
            ({"rental_start": self.inicio.isoformat()}, "errors.invalid_field"),
            ({"rental_start": self.inicio.isoformat(),
              "rental_end": (self.inicio - timedelta(days=1)).isoformat()},
             "errors.rental_end_before_start"),
            ({"rental_start": self.inicio.isoformat(),
              "rental_end": (self.inicio + timedelta(days=400)).isoformat()},
             "errors.invalid_field"),
        )
        for extra, error in casos:
            with self.subTest(extra=extra), self.assertRaises(AppError) as caja:
                create_need(PROYECTO_A, {**base, **extra}, ADMIN)
            self.assertEqual(error, caja.exception.message_key)

    def test_the_same_machine_in_the_same_period_is_a_duplicate_but_not_in_another(self):
        from app.services.proyect_material_need_service import create_need

        mismo = {"need_kind": "rental", "description": "Plataforma de tijera 10 m",
                 "quantity": 1, "rental_start": self.inicio.isoformat(),
                 "rental_end": self.fin.isoformat()}
        with self.assertRaises(AppError) as caja:
            create_need(PROYECTO_A, mismo, ADMIN)
        self.assertEqual("errors.need_duplicate_material", caja.exception.message_key)

        otro_mes = {**mismo, "rental_start": (self.inicio + timedelta(days=30)).isoformat(),
                    "rental_end": (self.inicio + timedelta(days=35)).isoformat()}
        self.assertEqual("rental", create_need(PROYECTO_A, otro_mes, ADMIN)["need_kind"])
        # Y una compra con las mismas palabras no choca con la renta.
        compra = create_need(PROYECTO_A, {"description": "Plataforma de tijera 10 m",
                                          "quantity": 1, "unit": "pza"}, ADMIN)
        self.assertEqual("material", compra["need_kind"])

    def test_a_rental_is_not_reviewed_against_the_warehouse(self):
        respuesta = self.client.post("/material-needs/%s/return" % N_PLATAFORMA,
                                     json={"note": "no se entiende"}, headers=self._compras())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_not_reviewable", self._error(respuesta))

    def test_purchasing_sees_the_rental_on_its_own_with_its_period(self):
        items = self.json(self.client.get("/material-needs/to-buy",
                                          headers=self._compras()))["items"]
        renta = next(g for g in items if g["need_kind"] == "rental")

        self.assertEqual(self.inicio.isoformat(), renta["rental_start"])
        self.assertEqual(self.fin.isoformat(), renta["rental_end"])
        self.assertEqual(self.inicio.isoformat(), renta["needed_by"])
        self.assertTrue(renta["projects"][0]["purchasable"])


class TestLaOrdenDeRenta(BaseRentas):

    def test_the_line_cost_is_the_rate_times_the_periods(self):
        respuesta = self._crear(lineas=[{"id_proyect_material_need": N_PLATAFORMA,
                                         "rental_rate": 1500, "rental_rate_unit": "day"}])

        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        linea = self.json(respuesta)["lines"][0]
        self.assertEqual("rental", linea["line_kind"])
        self.assertEqual(4500, linea["unit_cost"])  # 3 dias x 1500
        self.assertEqual(4500, self.json(respuesta)["quoted_total"])
        self.assertEqual(3, linea["rental"]["periods"])
        self.assertEqual("ordering", linea["rental"]["stage"])

    def test_weeks_and_months_round_up(self):
        from app.services.purchase_order_service import periodos_de_renta

        dia = self.inicio
        self.assertEqual(1, periodos_de_renta(dia, dia, "day"))
        self.assertEqual(2, periodos_de_renta(dia, dia + timedelta(days=8), "week"))
        self.assertEqual(1, periodos_de_renta(dia, dia + timedelta(days=6), "week"))
        self.assertEqual(2, periodos_de_renta(dia, dia + timedelta(days=30), "month"))

    def test_without_a_rate_the_order_cannot_be_sent(self):
        id_orden = self._id(self._crear(lineas=[{"id_proyect_material_need": N_PLATAFORMA}]))
        respuesta = self._accion(id_orden, "submit")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_without_costs", self._error(respuesta))

    def test_purchasing_can_add_a_rental_of_its_own(self):
        respuesta = self._crear(lineas=[{
            "line_kind": "rental", "description": "Generador 50 kVA", "quantity": 1,
            "rental_start": self.inicio.isoformat(),
            "rental_end": (self.inicio + timedelta(days=13)).isoformat(),
            "rental_rate": 3000, "rental_rate_unit": "week", "id_proyect": PROYECTO_A,
            "unit": "equipo"}])

        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        self.assertEqual(6000, self.json(respuesta)["lines"][0]["unit_cost"])

    def test_the_rental_is_not_received_in_the_warehouse(self):
        id_orden = self._orden_de_renta()
        linea = self._linea(id_orden)

        self.assertFalse(self._leer(id_orden, self._almacen())["actions"]["receive"])
        respuesta = self._recibir(id_orden, [
            {"id_purchase_order_line": linea["id_purchase_order_line"], "quantity": 1}])
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_line_is_rental", self._error(respuesta))


class TestLlegaYSeDevuelve(BaseRentas):

    def test_whoever_leads_the_job_marks_it_arrived_and_the_order_is_received(self):
        id_orden, id_linea = self._en_obra()

        orden = self._leer(id_orden)
        self.assertEqual("received", orden["order_status"])
        self.assertEqual(1, orden["lines"][0]["quantity_received"])
        self.assertEqual("on_site", orden["lines"][0]["rental"]["stage"])
        self.assertEqual(2, orden["lines"][0]["rental"]["days_left"])
        self.assertIn("rental_arrived", self._eventos(id_orden))

    def test_the_warehouse_can_mark_it_too_but_not_someone_unrelated(self):
        id_orden = self._orden_de_renta()
        id_linea = self._linea(id_orden)["id_purchase_order_line"]

        self.assertEqual(403, self._renta(id_linea, "arrive", self._nadie()).status_code)
        self.assertEqual(403, self._renta(id_linea, "arrive", self._compras()).status_code)
        self.assertEqual(200, self._renta(id_linea, "arrive", self._almacen()).status_code)

    def test_it_does_not_arrive_before_it_is_bought(self):
        id_orden = self._autorizada(lineas=[{"id_proyect_material_need": N_PLATAFORMA,
                                             "rental_rate": 1500}])
        id_linea = self._linea(id_orden)["id_purchase_order_line"]
        respuesta = self._renta(id_linea, "arrive")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_not_receivable", self._error(respuesta))

    def test_it_does_not_arrive_twice(self):
        _, id_linea = self._en_obra()
        again = self._renta(id_linea, "arrive")
        self.assertEqual(409, again.status_code)
        self.assertEqual("errors.rental_already_arrived", self._error(again))

    def test_a_purchase_line_has_no_rental_actions(self):
        id_orden = self._comprada()
        id_linea = self._linea(id_orden)["id_purchase_order_line"]
        respuesta = self._renta(id_linea, "arrive", self._almacen())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_line_not_rental", self._error(respuesta))

    def test_returning_it_closes_the_order(self):
        id_orden, id_linea = self._en_obra()

        respuesta = self._renta(id_linea, "return", note="Se entrego al chofer del proveedor")

        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        orden = self.json(respuesta)
        self.assertEqual("closed", orden["order_status"])
        self.assertEqual("returned", orden["lines"][0]["rental"]["stage"])
        self.assertEqual(409, self._renta(id_linea, "return").status_code)

    def test_it_cannot_be_returned_before_it_arrived_or_before_the_arrival_date(self):
        id_orden = self._orden_de_renta()
        id_linea = self._linea(id_orden)["id_purchase_order_line"]
        self.assertEqual("errors.rental_not_arrived",
                         self._error(self._renta(id_linea, "return")))

        self._renta(id_linea, "arrive")
        antes = (self.inicio - timedelta(days=1)).isoformat()
        self.assertEqual(400, self._renta(id_linea, "return", returned_date=antes).status_code)

    def test_the_project_shows_the_rental_and_what_its_leader_can_do(self):
        from app.services.purchase_order_service import rentas_de_necesidades

        _, id_linea = self._en_obra()
        with transaction_context() as db:
            renta = rentas_de_necesidades(
                db, [N_PLATAFORMA], {"id_user": USUARIO_SUPERVISOR,
                                     "id_permission": SUPERVISOR})[N_PLATAFORMA]

        self.assertEqual(id_linea, renta["id_purchase_order_line"])
        self.assertEqual({"arrive": False, "return": True, "extend": True,
                          "decide_extension": False}, renta["actions"])

    def test_the_need_counts_as_arrived_for_the_material_readiness(self):
        from app.services.project_management_service import material_readiness

        self._en_obra()
        with transaction_context() as db:
            listo = material_readiness(db, PROYECTO_A)
        # La renta llego; las otras necesidades abiertas de la obra A siguen sin pedirse.
        self.assertEqual(1, listo["received"])

    def test_a_project_is_not_completed_with_machinery_on_site(self):
        from app.services.project_management_service import transition_project

        _, id_linea = self._en_obra()
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_A).proyect_status = "in_progress"
            # Sin otras necesidades abiertas: lo unico que falta es devolver la renta.
            for need in db.scalars(select(ProyectMaterialNeed).where(
                    ProyectMaterialNeed.id_proyect == PROYECTO_A,
                    ProyectMaterialNeed.id_proyect_material_need != N_PLATAFORMA)):
                need.need_status = "cancelled"

        # De en proceso se pasa a recolectado (y de ahi a completado): ya ahi se exige.
        with self.assertRaises(AppError) as caja:
            transition_project(PROYECTO_A, {"status": "collected"}, ADMIN)
        self.assertEqual("errors.project_rental_not_returned", caja.exception.message_key)

        self._renta(id_linea, "return")
        try:
            transition_project(PROYECTO_A, {"status": "collected"}, ADMIN)
        except AppError as error:
            self.assertNotEqual("errors.project_rental_not_returned", error.message_key)


class TestLaProrroga(BaseRentas):

    def test_the_leader_asks_and_a_manager_approves_moving_the_end(self):
        _, id_linea = self._en_obra()
        nueva = (self.fin + timedelta(days=5)).isoformat()

        pedida = self._renta(id_linea, "extend", new_end=nueva, note="Se atraso el colado")
        self.assertEqual(200, pedida.status_code, pedida.get_data(as_text=True))
        self.assertEqual(409, self._renta(id_linea, "extend", new_end=nueva,
                                          note="otra vez").status_code)

        # Compras no autoriza compras; el gerente si.
        self.assertEqual(403, self._renta(id_linea, "extension", self._compras(),
                                          approve=True).status_code)
        decidida = self._renta(id_linea, "extension", self._gerente(1), approve=True)
        self.assertEqual(200, decidida.status_code, decidida.get_data(as_text=True))
        renta = self.json(decidida)["lines"][0]["rental"]
        self.assertEqual(nueva, renta["rental_end"])
        self.assertIsNone(renta["extension"])

    def test_the_extension_needs_a_later_date_and_a_reason(self):
        _, id_linea = self._en_obra()
        self.assertEqual(400, self._renta(id_linea, "extend", new_end=self.fin.isoformat(),
                                          note="Se atraso el colado").status_code)
        self.assertEqual(400, self._renta(
            id_linea, "extend", new_end=(self.fin + timedelta(days=3)).isoformat()).status_code)

    def test_nobody_decides_their_own_extension_and_rejecting_needs_a_reason(self):
        _, id_linea = self._en_obra()
        self._renta(id_linea, "extend", self._gerente(1),
                    new_end=(self.fin + timedelta(days=3)).isoformat(), note="Falta terminar")

        propia = self._renta(id_linea, "extension", self._gerente(1), approve=True)
        self.assertEqual(403, propia.status_code)
        self.assertEqual(400, self._renta(id_linea, "extension", self._gerente(2),
                                          approve=False).status_code)
        rechazada = self._renta(id_linea, "extension", self._gerente(2), approve=False,
                                note="Que se devuelva y se renta otra despues")
        self.assertEqual(200, rechazada.status_code)
        self.assertEqual(self.fin.isoformat(),
                         self.json(rechazada)["lines"][0]["rental"]["rental_end"])

    def test_asking_warns_the_authorizers_and_deciding_warns_who_asked(self):
        _, id_linea = self._en_obra()
        self._renta(id_linea, "extend", new_end=(self.fin + timedelta(days=3)).isoformat(),
                    note="Se atraso el colado")
        self.assertIn("purchase_rental_extension_requested",
                      [a[0] for a in self._avisos(31)])

        self._renta(id_linea, "extension", self._gerente(1), approve=True)
        self.assertIn("purchase_rental_extension_decided",
                      [a[0] for a in self._avisos(USUARIO_SUPERVISOR)])


class TestRentasActivasYAvisos(BaseRentas):

    def test_the_active_rentals_list_shows_what_is_on_site_and_not_what_was_returned(self):
        _, id_linea = self._en_obra()

        activas = self.json(self.client.get("/purchase-rentals", headers=self._compras()))
        self.assertEqual(1, activas["total"])
        self.assertEqual(1, activas["on_site"])
        self.assertEqual("PRJ-10", activas["items"][0]["project"]["folio"])
        self.assertEqual("Ferreteria Norte", activas["items"][0]["supplier_name"])

        self._renta(id_linea, "return")
        self.assertEqual(0, self.json(self.client.get("/purchase-rentals",
                                                      headers=self._compras()))["total"])
        todas = self.json(self.client.get("/purchase-rentals?status=all",
                                          headers=self._compras()))
        self.assertEqual(1, todas["total"])

    def test_the_list_is_for_whoever_sees_the_orders(self):
        self.assertIn(self.client.get("/purchase-rentals", headers=self._nadie()).status_code,
                      (401, 403))

    def _vence_en(self, dias):
        with transaction_context() as db:
            for linea in db.scalars(select(PurchaseOrderLine).where(
                    PurchaseOrderLine.line_kind == "rental")):
                linea.rental_end = hoy_negocio() + timedelta(days=dias)
                linea.rental_start = min(linea.rental_start, linea.rental_end)
                linea.rental_arrived_date = linea.rental_start

    def _avisos_de_renta(self, id_user):
        with transaction_context() as db:
            return [n.notification_type for n in db.scalars(select(Notification).where(
                Notification.id_user_recipient == id_user,
                Notification.notification_type.like("purchase_rental_%")))]

    def test_it_warns_once_when_it_is_due_soon_and_once_when_it_is_overdue(self):
        from app.services.purchase_order_service import avisar_rentas_por_vencer

        self._en_obra()
        self._vence_en(10)
        self.assertEqual(0, avisar_rentas_por_vencer())

        self._vence_en(1)
        self.assertEqual(1, avisar_rentas_por_vencer())
        self.assertEqual(0, avisar_rentas_por_vencer())
        self.assertEqual(["purchase_rental_due"], self._avisos_de_renta(USUARIO_SUPERVISOR))
        self.assertEqual(["purchase_rental_due"], self._avisos_de_renta(COMPRAS_1))

        # Pasan los dias: el aviso de "vence pronto" quedo de antes del fin, y ya vencio.
        self._vence_en(-1)
        with transaction_context() as db:
            for linea in db.scalars(select(PurchaseOrderLine).where(
                    PurchaseOrderLine.line_kind == "rental")):
                linea.rental_reminder_date = linea.rental_end - timedelta(days=1)
        self.assertEqual(1, avisar_rentas_por_vencer())
        self.assertEqual(0, avisar_rentas_por_vencer())
        self.assertEqual(["purchase_rental_due", "purchase_rental_overdue"],
                         self._avisos_de_renta(USUARIO_SUPERVISOR))

    def test_a_returned_rental_warns_nobody(self):
        from app.services.purchase_order_service import avisar_rentas_por_vencer

        _, id_linea = self._en_obra()
        self._renta(id_linea, "return")
        self._vence_en(-3)
        self.assertEqual(0, avisar_rentas_por_vencer())


class TestElRegistroDeLosAvisos(BaseRentas):

    def test_the_rental_notification_types_are_allowed_by_the_database(self):
        from pathlib import Path

        texto = (Path(__file__).resolve().parents[3] / "database" / "migrations"
                 / "20261007100000_tipos_de_notificacion_unica_fuente.sql").read_text("utf-8")
        for tipo in ("purchase_rental_due", "purchase_rental_overdue",
                     "purchase_rental_extension_requested", "purchase_rental_extension_decided"):
            self.assertIn("'%s'" % tipo, texto)

    def test_the_reminder_job_is_scheduled_on_a_queue_the_worker_consumes(self):
        from app.config.celery_config import CeleryConfig
        from app.jobs.beat_schedule import BEAT_SCHEDULE

        tareas = [v["task"] for v in BEAT_SCHEDULE.values()]
        self.assertIn("app.jobs.tasks_purchases.notify_rentals_due", tareas)
        self.assertFalse(any(patron.startswith("app.jobs.tasks_purchases")
                             for patron in CeleryConfig.task_routes))
