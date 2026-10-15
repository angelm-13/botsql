from __future__ import annotations

import contextlib
import copy
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

from sqlalchemy import delete, select, update

from app.jobs import tasks_kpis
from app.jobs.beat_schedule import BEAT_SCHEDULE
from app.kpis import frecuencia
from app.kpis.registry import KPI_POR_CLAVE, KPI_REGISTRY, MODULO_POR_CLAVE
from app.kpis.dimensiones import etiquetas_de_dimension
from app.kpis.modulos import restaurante as kpis_restaurante
from app.kpis.modulos.restaurante import (
    definiciones, ventas_por_mesero_query, ventas_restaurante_query,
)
from app.models import (
    KpiDefinition, KpiSnapshot, Proyect, RestaurantCashSession, RestaurantDish, RestaurantOrder, RestaurantOrderItem,
    RestaurantTable, RestaurantVisit, RestaurantWaiter, User,
)
from app.models.session import engine, transaction_context
from app.routes.kpi import _totales
from app.services.restaurant_service import RestaurantService

# Mismo criterio que test_kpi_incidentes.py: solo contra PostgreSQL real, sobre el esquema real y el
# bootstrap de siempre (user=1, proyect=1, customer_supplier=1), con ids propios (970+) para no
# chocar con otros archivos de prueba.
ADMIN_ID = 1
PROYECTO_A = 970
PROYECTO_B = 971
MESERO_ROSA = 9701
MESERO_LUIS = 9702
MESA = 9701
PLATILLO = 9701
VISITA_A = 9701
VISITA_B = 9702
VISITA_A2 = 9703      # mesa 8, la atiende Luis
VISITA_LLEVAR = 9704  # para llevar, sin mesa
MESA_2 = 9702
PLATILLO_2 = 9702
CAJERO_A = 9701
CAJERO_B = 9702

DESDE = date(2026, 9, 1)
HASTA = date(2026, 9, 30)
DIA = datetime(2026, 9, 15, 13, 0)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class KpiRestauranteTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for id_proyect in (PROYECTO_A, PROYECTO_B):
                db.add(Proyect(
                    id_proyect=id_proyect, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Restaurante KPI {id_proyect}", created_by=ADMIN_ID,
                ))
            db.flush()
            for id_mesero, nombre in ((MESERO_ROSA, "Rosa"), (MESERO_LUIS, "Luis")):
                db.add(RestaurantWaiter(
                    id_restaurant_waiter=id_mesero, id_proyect=PROYECTO_A, name=nombre, nickname=nombre,
                    created_by=ADMIN_ID,
                ))
            for id_usuario in (CAJERO_A, CAJERO_B):
                db.add(User(
                    id_user=id_usuario, created_by=ADMIN_ID, full_name=f"Cajero {id_usuario}", id_permission=1,
                    id_proyect=1, id_status=1, supervisor=ADMIN_ID, user_type="employee", is_employee=True,
                    username=f"kpi-restaurante-test-{id_usuario}",
                ))
            db.add(RestaurantTable(id_restaurant_table=MESA, id_proyect=PROYECTO_A, number=7, created_by=ADMIN_ID))
            db.add(RestaurantTable(id_restaurant_table=MESA_2, id_proyect=PROYECTO_A, number=8, created_by=ADMIN_ID))
            db.add(RestaurantDish(
                id_restaurant_dish=PLATILLO, id_proyect=PROYECTO_A, title="Taco", price=50, created_by=ADMIN_ID,
            ))
            db.add(RestaurantDish(
                id_restaurant_dish=PLATILLO_2, id_proyect=PROYECTO_A, title="Torta", price=70, created_by=ADMIN_ID,
            ))
            db.flush()
            db.add(RestaurantVisit(
                id_restaurant_visit=VISITA_A2, id_proyect=PROYECTO_A, id_restaurant_table=MESA_2,
                id_restaurant_waiter=MESERO_LUIS, created_by=ADMIN_ID,
            ))
            db.add(RestaurantVisit(
                id_restaurant_visit=VISITA_LLEVAR, id_proyect=PROYECTO_A, service_type="para_llevar",
                daily_number=1, service_date=DIA.date(), created_by=ADMIN_ID,
            ))
            db.add(RestaurantVisit(
                id_restaurant_visit=VISITA_A, id_proyect=PROYECTO_A, id_restaurant_table=MESA,
                id_restaurant_waiter=MESERO_ROSA, created_by=ADMIN_ID,
            ))
            # Una visita "para llevar" no lleva mesa, pero el CHECK real exige numero del dia y fecha.
            db.add(RestaurantVisit(
                id_restaurant_visit=VISITA_B, id_proyect=PROYECTO_B, service_type="para_llevar",
                daily_number=1, service_date=DIA.date(), created_by=ADMIN_ID,
            ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(RestaurantCashSession).where(
                RestaurantCashSession.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            ids_orden = select(RestaurantOrder.id_restaurant_order).where(
                RestaurantOrder.id_proyect.in_([PROYECTO_A, PROYECTO_B]))
            db.execute(delete(RestaurantOrderItem).where(RestaurantOrderItem.id_restaurant_order.in_(ids_orden)))
            db.execute(delete(RestaurantOrder).where(RestaurantOrder.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(RestaurantVisit).where(RestaurantVisit.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(RestaurantTable).where(RestaurantTable.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(RestaurantDish).where(RestaurantDish.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(RestaurantWaiter).where(RestaurantWaiter.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_A, PROYECTO_B])))
            db.execute(delete(User).where(User.id_user.in_([CAJERO_A, CAJERO_B])))

    def _orden(self, id_orden, renglones, *, estado="pagado", pagada=DIA, mesero=MESERO_ROSA,
               propina=0, proyecto=PROYECTO_A, borrada=None, visita=None, enviada=None, lista=None, entregada=None):
        """Una orden con sus renglones [(cantidad, precio)] o [(cantidad, precio, platillo)]."""
        with transaction_context() as db:
            db.add(RestaurantOrder(
                id_restaurant_order=id_orden, id_proyect=proyecto,
                id_restaurant_visit=visita or (VISITA_A if proyecto == PROYECTO_A else VISITA_B),
                id_restaurant_waiter=mesero, status=estado, tip_amount=propina,
                paid_at=pagada if estado == "pagado" else None, deletion_date=borrada,
                sent_at=enviada, ready_at=lista, delivered_at=entregada, created_by=ADMIN_ID,
            ))
            db.flush()
            for renglon in renglones:
                cantidad, precio, *resto = renglon
                db.add(RestaurantOrderItem(
                    id_restaurant_order=id_orden, id_restaurant_dish=resto[0] if resto else PLATILLO,
                    quantity=cantidad, unit_price=precio, created_by=ADMIN_ID,
                ))

    def _sesion(self, id_sesion, diferencia, *, cierra=CAJERO_A, estado="closed", cerrada=DIA, proyecto=PROYECTO_A):
        with transaction_context() as db:
            db.add(RestaurantCashSession(
                id_restaurant_cash_session=id_sesion, id_proyect=proyecto, opened_by_id=ADMIN_ID,
                opening_amount=500, closed_by_id=cierra if estado == "closed" else None,
                closed_at=cerrada if estado == "closed" else None, difference=diferencia if estado == "closed" else None,
                status=estado, created_by=ADMIN_ID,
            ))

    def _consulta(self, query, actor_project=PROYECTO_A, desde=DESDE, hasta=HASTA):
        with transaction_context() as db:
            return query(db, desde, hasta, {}, actor_project)

    def _ventas(self, actor_project=PROYECTO_A, desde=DESDE, hasta=HASTA):
        with transaction_context() as db:
            return ventas_restaurante_query(db, desde, hasta, {}, actor_project)

    def _por_mesero(self, actor_project=PROYECTO_A, desde=DESDE, hasta=HASTA):
        with transaction_context() as db:
            return ventas_por_mesero_query(db, desde, hasta, {}, actor_project)

    # --- la regla de venta -------------------------------------------------

    def test_orden_pagada_de_3x50_y_1x100_vale_250(self):
        self._orden(97001, [(3, 50), (1, 100)])
        self.assertEqual([(None, DIA.date(), Decimal("250.00"))], self._ventas())

    def test_la_propina_no_cuenta_como_venta(self):
        self._orden(97001, [(3, 50), (1, 100)], propina=40)
        self.assertEqual(Decimal("250.00"), self._ventas()[0][2])

    def test_una_propina_no_especificada_es_cero_y_la_venta_sigue_siendo_el_subtotal(self):
        self._orden(97001, [(2, 50)])
        with transaction_context() as db:
            propina = db.scalar(select(RestaurantOrder.tip_amount).where(RestaurantOrder.id_restaurant_order == 97001))
        self.assertEqual(Decimal("0"), propina)
        self.assertEqual(Decimal("100.00"), self._ventas()[0][2])

    def test_una_orden_que_no_esta_pagada_no_cuenta(self):
        for id_orden, estado in enumerate(("borrador", "pedido", "en_preparacion", "listo_para_entrega", "entregado"), 97010):
            self._orden(id_orden, [(1, 100)], estado=estado)
        self.assertEqual([], self._ventas())
        self.assertEqual([], self._por_mesero())

    def test_una_orden_borrada_no_cuenta(self):
        self._orden(97001, [(1, 100)])
        self._orden(97002, [(1, 100)], borrada=datetime(2026, 9, 16))
        self.assertEqual(Decimal("100.00"), self._ventas()[0][2])

    def test_se_cuenta_el_dia_del_cobro_y_el_rango_incluye_sus_extremos(self):
        # Horas en UTC; el dia es el LOCAL (UTC-6): 1-sep 00:05, 30-sep 23:55, 31-ago 23:59 y 1-oct 00:00 locales.
        self._orden(97001, [(1, 10)], pagada=datetime(2026, 9, 1, 6, 5))
        self._orden(97002, [(1, 20)], pagada=datetime(2026, 10, 1, 5, 55))
        self._orden(97003, [(1, 400)], pagada=datetime(2026, 9, 1, 5, 59))
        self._orden(97004, [(1, 800)], pagada=datetime(2026, 10, 1, 6, 0))
        self.assertEqual(
            [(None, date(2026, 9, 1), Decimal("10.00")), (None, date(2026, 9, 30), Decimal("20.00"))],
            self._ventas(),
        )

    def test_suma_las_ordenes_del_mismo_dia(self):
        self._orden(97001, [(1, 100)])
        self._orden(97002, [(2, 25)], mesero=MESERO_LUIS)
        self.assertEqual([(None, DIA.date(), Decimal("150.00"))], self._ventas())

    def test_el_alcance_por_proyecto_aisla_los_restaurantes(self):
        self._orden(97001, [(1, 100)])
        self._orden(97002, [(1, 7)], proyecto=PROYECTO_B, mesero=None)
        self.assertEqual(Decimal("100.00"), self._ventas(PROYECTO_A)[0][2])
        self.assertEqual(Decimal("7.00"), self._ventas(PROYECTO_B)[0][2])
        # Superusuario (sin proyecto): todo lo que haya cobrado en el rango.
        self.assertEqual(Decimal("107.00"), self._ventas(None)[0][2])

    # --- ventas por mesero ---------------------------------------------------

    def test_ventas_por_mesero_agrupa_por_el_mesero_de_la_orden(self):
        self._orden(97001, [(3, 50), (1, 100)], mesero=MESERO_ROSA)
        self._orden(97002, [(2, 30)], mesero=MESERO_LUIS)
        self._orden(97003, [(1, 10)], mesero=MESERO_ROSA)
        self.assertEqual(
            {(MESERO_ROSA, Decimal("260.00")), (MESERO_LUIS, Decimal("60.00"))},
            {(fila[0], fila[2]) for fila in self._por_mesero()},
        )

    def test_una_orden_sin_mesero_no_se_pierde_regresa_entidad_nula(self):
        self._orden(97001, [(1, 100)], mesero=MESERO_ROSA)
        self._orden(97002, [(1, 40)], mesero=None)
        filas = {fila[0]: fila[2] for fila in self._por_mesero()}
        self.assertEqual({MESERO_ROSA: Decimal("100.00"), None: Decimal("40.00")}, filas)
        # Y el total por mesero cuadra con las ventas del restaurante.
        self.assertEqual(sum(filas.values()), self._ventas()[0][2])

    def test_sin_ordenes_no_hay_filas_y_nunca_se_divide_entre_cero(self):
        self.assertEqual([], self._ventas())
        self.assertEqual([], self._por_mesero())

    # --- de la consulta al Dashboard: snapshot, "Sin asignar" y "sin datos" ---

    def _correr_job(self, *claves):
        """Corre la tarea nocturna solo con los KPIs de restaurante pedidos (todos, si no se pide ninguno);
        devuelve {clave: id_kpi_definition}."""
        kpis = [k for k in definiciones() if not claves or k.clave in claves]
        creadas = []
        ids = {}
        with transaction_context() as db:
            for kpi in kpis:
                fila = db.scalar(select(KpiDefinition).where(KpiDefinition.clave == kpi.clave))
                if fila is None:
                    fila = KpiDefinition(
                        clave=kpi.clave, etiqueta=kpi.etiqueta, modulo=kpi.modulo,
                        dimensiones=list(kpi.dimensiones), unidad=kpi.unidad,
                    )
                    db.add(fila)
                    db.flush()
                    creadas.append(fila.id_kpi_definition)
                ids[kpi.clave] = fila.id_kpi_definition
        self.addCleanup(self._borrar_definiciones, ids, creadas)
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", tuple(kpis)):
            tasks_kpis.recalcular_kpi_snapshots_rango(DESDE, HASTA)
        return ids

    def _borrar_definiciones(self, ids, creadas):
        with transaction_context() as db:
            db.execute(delete(KpiSnapshot).where(KpiSnapshot.id_kpi_definition.in_(list(ids.values()))))
            if creadas:
                db.execute(delete(KpiDefinition).where(KpiDefinition.id_kpi_definition.in_(creadas)))

    def test_la_orden_sin_mesero_sale_como_sin_asignar_en_la_lista_y_en_el_total(self):
        self._orden(97001, [(3, 50), (1, 100)], mesero=MESERO_ROSA)
        self._orden(97002, [(1, 40)], mesero=None)
        ids = self._correr_job()
        with transaction_context() as db:
            rango = _totales(db, ids["ventas_por_mesero"], DESDE, HASTA, PROYECTO_A, None,
                             "id_restaurant_waiter", "suma", sin_asignar=KPI_POR_CLAVE["ventas_por_mesero"].sin_asignar)
            sin_la_bandera = _totales(db, ids["ventas_por_mesero"], DESDE, HASTA, PROYECTO_A, None,
                                      "id_restaurant_waiter", "suma")
        self.assertTrue(KPI_POR_CLAVE["ventas_por_mesero"].sin_asignar)
        self.assertEqual({str(MESERO_ROSA): 250.0, "sin_asignar": 40.0}, rango["por_empleado"])
        self.assertEqual(290.0, rango["total"])
        # Con la bandera apagada (lo que hacen los 24 KPIs de siempre) la fila se descarta de la lista y del total.
        self.assertEqual({str(MESERO_ROSA): 250.0}, sin_la_bandera["por_empleado"])
        self.assertEqual(250.0, sin_la_bandera["total"])

    def test_el_snapshot_de_ventas_restaurante_es_global_y_sin_datos_da_cero(self):
        self._orden(97001, [(3, 50), (1, 100)])
        ids = self._correr_job()
        with transaction_context() as db:
            con_datos = _totales(db, ids["ventas_restaurante"], DESDE, HASTA, PROYECTO_A, None, None, "suma")
            otro_proyecto = _totales(db, ids["ventas_restaurante"], DESDE, HASTA, PROYECTO_B, None, None, "suma")
        self.assertEqual(250.0, con_datos["total"])
        self.assertEqual(0.0, otro_proyecto["total"])

    # --- una sola regla de venta ---------------------------------------------

    def test_el_kpi_y_el_servicio_del_restaurante_cuentan_la_misma_venta(self):
        self._orden(97001, [(3, 50), (1, 100)], propina=40)
        self._orden(97002, [(2, 30)], mesero=MESERO_LUIS)
        self._orden(97003, [(1, 999)], estado="entregado")
        self._orden(97004, [(1, 999)], borrada=datetime(2026, 9, 16))
        kpi = sum(fila[2] for fila in self._ventas())
        with transaction_context() as db:
            servicio = RestaurantService(db, PROYECTO_A, ADMIN_ID)
            kpis_del_servicio = servicio.kpis()["total_sales"]
            reporte = servicio.sales_report("2026-09-01", "2026-09-30")["total_sales"]
        self.assertEqual(310.0, float(kpi))
        self.assertEqual(float(kpi), kpis_del_servicio)
        self.assertEqual(float(kpi), reporte)

    # === el resto de la Fase 2 ==========================================================

    def _rango(self, ids, clave, campo_json, agregacion, **kw):
        with transaction_context() as db:
            return _totales(db, ids[clave], DESDE, HASTA, PROYECTO_A, None, campo_json, agregacion,
                            sin_asignar=KPI_POR_CLAVE[clave].sin_asignar, **kw)

    # --- ticket promedio ---------------------------------------------------------

    def test_ticket_promedio_de_dos_ordenes_de_250_y_100_es_175(self):
        self._orden(97001, [(3, 50), (1, 100)])
        self._orden(97002, [(2, 50)])
        self.assertEqual([(None, DIA.date(), Decimal("175.00"), 2)], self._consulta(kpis_restaurante.ticket_promedio_query))

    def test_el_ticket_de_un_rango_pondera_por_ordenes_no_promedia_los_dias(self):
        # Dia 1: una orden de 250. Dia 2: dos ordenes de 100 y 50. Promedio simple de los dias: (250 + 75) / 2.
        # Promedio real: 400 / 3 ordenes.
        self._orden(97001, [(3, 50), (1, 100)], pagada=datetime(2026, 9, 1, 12))
        self._orden(97002, [(2, 50)], pagada=datetime(2026, 9, 2, 12))
        self._orden(97003, [(1, 50)], pagada=datetime(2026, 9, 2, 13))
        ids = self._correr_job("ticket_promedio")
        self.assertEqual(133.33, round(self._rango(ids, "ticket_promedio", None, "promedio_ponderado")["total"], 2))

    def test_el_ticket_cuenta_tambien_la_orden_cobrada_sin_renglones_como_el_servicio(self):
        self._orden(97001, [(1, 100)])
        self._orden(97002, [])
        (fila,) = self._consulta(kpis_restaurante.ticket_promedio_query)
        self.assertEqual((Decimal("50.00"), 2), (fila[2], fila[3]))
        with transaction_context() as db:
            self.assertEqual(50.0, RestaurantService(db, PROYECTO_A, ADMIN_ID).kpis()["avg_ticket"])

    def test_sin_ordenes_el_ticket_no_tiene_filas(self):
        self.assertEqual([], self._consulta(kpis_restaurante.ticket_promedio_query))
        ids = self._correr_job("ticket_promedio")
        rango = self._rango(ids, "ticket_promedio", None, "promedio_ponderado")
        self.assertEqual(0.0, rango["total"])

    # --- propinas -------------------------------------------------------------

    def test_propinas_suman_las_de_las_ordenes_cobradas_y_una_no_especificada_es_cero(self):
        self._orden(97001, [(1, 100)], propina=30)
        self._orden(97002, [(1, 100)])  # sin propina: tip_amount = 0
        self._orden(97003, [(1, 100)], propina=99, estado="entregado")  # sin cobrar: no cuenta
        self.assertEqual([(None, DIA.date(), Decimal("30.00"))], self._consulta(kpis_restaurante.propinas_restaurante_query))

    def test_una_orden_cobrada_sin_propina_da_cero_y_sin_ordenes_no_hay_filas(self):
        self._orden(97001, [(1, 100)])
        self.assertEqual(Decimal("0"), self._consulta(kpis_restaurante.propinas_restaurante_query)[0][2])
        self._limpiar()
        self.assertEqual([], self._consulta(kpis_restaurante.propinas_restaurante_query))

    def test_las_propinas_no_tienen_version_por_mesero(self):
        claves = {kpi.clave for kpi in definiciones()}
        self.assertIn("propinas_restaurante", claves)
        self.assertFalse([c for c in claves if "propina" in c and "mesero" in c])
        self.assertEqual(("global",), KPI_POR_CLAVE["propinas_restaurante"].dimensiones)

    def test_propina_pct_de_venta_es_propina_entre_subtotal(self):
        self._orden(97001, [(3, 50), (1, 100)], propina=25)
        self.assertEqual(
            [(None, DIA.date(), Decimal("10.00"), Decimal("250.00"))],
            self._consulta(kpis_restaurante.propina_pct_de_venta_query),
        )

    def test_el_porcentaje_de_un_rango_es_propinas_entre_venta_no_el_promedio_de_los_dias(self):
        self._orden(97001, [(3, 50), (1, 100)], propina=25, pagada=datetime(2026, 9, 1, 12))  # 10 %
        self._orden(97002, [(1, 100)], propina=0, pagada=datetime(2026, 9, 2, 12))              # 0 %
        ids = self._correr_job("propina_pct_de_venta")
        self.assertEqual(7.14, round(self._rango(ids, "propina_pct_de_venta", None, "promedio_ponderado")["total"], 2))

    def test_un_dia_sin_venta_no_divide_entre_cero(self):
        self._orden(97001, [], propina=20)  # cobrada, sin renglones: subtotal 0
        self.assertEqual([], self._consulta(kpis_restaurante.propina_pct_de_venta_query))
        self._limpiar()
        self.assertEqual([], self._consulta(kpis_restaurante.propina_pct_de_venta_query))

    # --- platillos ------------------------------------------------------------

    def test_platillos_mas_vendidos_suma_cantidades_de_ordenes_cobradas(self):
        self._orden(97001, [(3, 50), (1, 70, PLATILLO_2)])
        self._orden(97002, [(2, 50)])
        self._orden(97003, [(9, 50)], estado="entregado")  # sin cobrar
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.platillos_mas_vendidos_query)}
        self.assertEqual({PLATILLO: 5, PLATILLO_2: 1}, filas)

    def test_el_top_se_corta_al_leer_y_el_nombre_viene_del_backend(self):
        self._orden(97001, [(3, 50), (1, 70, PLATILLO_2)])
        ids = self._correr_job("platillos_mas_vendidos")
        rango = self._rango(ids, "platillos_mas_vendidos", "id_restaurant_dish", "suma",
                            limite=KPI_POR_CLAVE["platillos_mas_vendidos"].limite_categorias)
        self.assertEqual(10, KPI_POR_CLAVE["platillos_mas_vendidos"].limite_categorias)
        self.assertEqual({str(PLATILLO): 3.0, str(PLATILLO_2): 1.0}, rango["por_empleado"])
        with transaction_context() as db:
            etiquetas = etiquetas_de_dimension(db, "platillo", (rango,), True)
        self.assertEqual({"Taco", "Torta"}, {etiquetas[str(PLATILLO)], etiquetas[str(PLATILLO_2)]})
        with transaction_context() as db:
            solo_uno = _totales(db, ids["platillos_mas_vendidos"], DESDE, HASTA, PROYECTO_A, None,
                                "id_restaurant_dish", "suma", limite=1)
        self.assertEqual({str(PLATILLO): 3.0}, solo_uno["por_empleado"])
        self.assertEqual(4.0, solo_uno["total"], "el total sigue siendo el de TODOS los platillos")

    def test_frecuencia_cuenta_ordenes_distintas_no_cantidades(self):
        # Orden 1: tacos en dos renglones (3 + 2). Orden 2: 1 taco. Cantidad: 6. Ordenes con taco: 2.
        self._orden(97001, [(3, 50), (2, 50)])
        self._orden(97002, [(1, 50), (1, 70, PLATILLO_2)])
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.frecuencia_por_platillo_query)}
        self.assertEqual({PLATILLO: 2, PLATILLO_2: 1}, filas)
        cantidades = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.platillos_mas_vendidos_query)}
        self.assertEqual(6, cantidades[PLATILLO])

    # --- mesas ----------------------------------------------------------------

    def test_top_mesas_suma_venta_por_mesa_de_la_visita_y_deja_fuera_el_mostrador(self):
        self._orden(97001, [(3, 50), (1, 100)], visita=VISITA_A)      # mesa 7: 250
        self._orden(97002, [(2, 50)], visita=VISITA_A2)               # mesa 8: 100
        self._orden(97003, [(1, 40)], visita=VISITA_A)                # mesa 7: +40
        self._orden(97004, [(1, 999)], visita=VISITA_LLEVAR)          # para llevar: sin mesa
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.top_mesas_query)}
        self.assertEqual({MESA: Decimal("290.00"), MESA_2: Decimal("100.00")}, filas)
        with transaction_context() as db:
            self.assertEqual("Mesa 7", etiquetas_de_dimension(db, "mesa", ({"por_empleado": {str(MESA): 1.0}},), True)[str(MESA)])

    # --- servicios y tiempos ---------------------------------------------------

    def test_servicios_por_mesero_cuenta_las_ordenes_enviadas_a_cocina(self):
        envio = datetime(2026, 9, 15, 12, 0)
        self._orden(97001, [(1, 10)], mesero=MESERO_ROSA, enviada=envio)
        self._orden(97002, [(1, 10)], mesero=MESERO_ROSA, enviada=envio, estado="entregado")  # sin cobrar: cuenta
        self._orden(97003, [(1, 10)], mesero=MESERO_LUIS, enviada=envio)
        self._orden(97004, [(1, 10)], mesero=MESERO_LUIS, estado="borrador")                  # nunca se envio
        self._orden(97005, [(1, 10)], mesero=MESERO_LUIS, enviada=envio, borrada=datetime(2026, 9, 16))
        self._orden(97006, [(1, 10)], mesero=None, enviada=envio)
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.servicios_por_mesero_query)}
        self.assertEqual({MESERO_ROSA: 2, MESERO_LUIS: 1, None: 1}, filas)

    def test_tiempo_de_entrega_promedia_minutos_de_ready_a_delivered_ponderado_por_ordenes(self):
        lista = datetime(2026, 9, 15, 13, 0)
        self._orden(97001, [(1, 10)], lista=lista, entregada=datetime(2026, 9, 15, 13, 12))
        self._orden(97002, [(1, 10)], lista=lista, entregada=datetime(2026, 9, 15, 13, 20))
        self._orden(97003, [(1, 10)], lista=lista)                      # sin entrega: no cuenta
        self._orden(97004, [(1, 10)], entregada=datetime(2026, 9, 15, 13, 50))  # sin "lista": no cuenta
        self.assertEqual([(None, DIA.date(), Decimal("16.00"), 2)], self._consulta(kpis_restaurante.tiempo_de_entrega_query))
        self.assertEqual("minutos", KPI_POR_CLAVE["tiempo_de_entrega"].unidad)
        self.assertEqual("bajo_es_mejor", KPI_POR_CLAVE["tiempo_de_entrega"].direccion)

    def test_tiempo_de_entrega_de_un_rango_pondera_por_ordenes(self):
        lista = datetime(2026, 9, 1, 13, 0)
        self._orden(97001, [(1, 10)], lista=lista, entregada=datetime(2026, 9, 1, 13, 30))                  # dia 1: 30
        self._orden(97002, [(1, 10)], lista=datetime(2026, 9, 2, 13), entregada=datetime(2026, 9, 2, 13, 10))  # dia 2: 10
        self._orden(97003, [(1, 10)], lista=datetime(2026, 9, 2, 14), entregada=datetime(2026, 9, 2, 14, 10))  # dia 2: 10
        ids = self._correr_job("tiempo_de_entrega")
        self.assertEqual(16.67, round(self._rango(ids, "tiempo_de_entrega", None, "promedio_ponderado")["total"], 2))

    def test_sin_ordenes_entregadas_no_hay_tiempo_de_entrega(self):
        self.assertEqual([], self._consulta(kpis_restaurante.tiempo_de_entrega_query))

    def test_el_tiempo_de_entrega_coincide_con_el_del_servicio_cuando_todo_lo_entregado_esta_cobrado(self):
        lista = datetime(2026, 9, 15, 13, 0)
        self._orden(97001, [(1, 10)], lista=lista, entregada=datetime(2026, 9, 15, 13, 12))
        self._orden(97002, [(1, 10)], lista=lista, entregada=datetime(2026, 9, 15, 13, 20))
        kpi = self._consulta(kpis_restaurante.tiempo_de_entrega_query)[0][2]
        with transaction_context() as db:
            servicio = RestaurantService(db, PROYECTO_A, ADMIN_ID).kpis()["avg_minutes_from_ready_to_delivered"]
        self.assertEqual(float(kpi), servicio)

    # --- caja -------------------------------------------------------------------

    def test_desviacion_de_caja_suma_el_absoluto_de_cada_sesion_por_cajero(self):
        self._sesion(97001, Decimal("-50.00"), cierra=CAJERO_A)
        self._sesion(97002, Decimal("20.00"), cierra=CAJERO_A)
        self._sesion(97003, Decimal("5.00"), cierra=CAJERO_B)
        self._sesion(97004, None, estado="open")  # abierta: no cuenta
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.diferencia_de_caja_query)}
        self.assertEqual({CAJERO_A: Decimal("70.00"), CAJERO_B: Decimal("5.00")}, filas)

    def test_un_sobrante_y_un_faltante_del_mismo_dia_no_se_compensan(self):
        self._sesion(97001, Decimal("100.00"), cierra=CAJERO_A)
        self._sesion(97002, Decimal("-100.00"), cierra=CAJERO_A)
        (fila,) = self._consulta(kpis_restaurante.diferencia_de_caja_query)
        self.assertEqual(Decimal("200.00"), fila[2])

    def test_desviacion_de_caja_es_bajo_es_mejor_conserva_su_clave_y_no_se_siembra_a_ningun_rol(self):
        from scripts.seed_kpi_permissions import ASIGNACIONES

        kpi = KPI_POR_CLAVE["diferencia_de_caja"]
        self.assertEqual("bajo_es_mejor", kpi.direccion)
        self.assertEqual("Desviación de caja", kpi.etiqueta)
        asignadas = {clave for perfil in ASIGNACIONES.values() for rol in perfil for clave in rol.kpis}
        self.assertFalse(asignadas & {k.clave for k in definiciones()}, "ningun KPI de restaurante se siembra a un rol")

    def test_propinas_son_neutrales_con_numero_por_omision_y_el_porcentaje_es_alto_es_mejor(self):
        self.assertEqual("neutral", KPI_POR_CLAVE["propinas_restaurante"].direccion)
        self.assertEqual("numero", KPI_POR_CLAVE["propinas_restaurante"].grafica_default)
        self.assertEqual("alto_es_mejor", KPI_POR_CLAVE["propina_pct_de_venta"].direccion)
        self.assertEqual(10, KPI_POR_CLAVE["frecuencia_por_platillo"].limite_categorias)

    def test_tiempo_de_entrega_cuenta_la_orden_entregada_aunque_no_este_cobrada(self):
        lista = datetime(2026, 9, 15, 13, 0)
        self._orden(97001, [(1, 10)], estado="entregado", lista=lista, entregada=datetime(2026, 9, 15, 13, 10))
        self.assertEqual([(None, DIA.date(), Decimal("10.00"), 1)], self._consulta(kpis_restaurante.tiempo_de_entrega_query))

    def test_una_sesion_sin_cajero_sale_como_sin_asignar(self):
        self._sesion(97001, Decimal("-10.00"), cierra=None)
        ids = self._correr_job("diferencia_de_caja")
        rango = self._rango(ids, "diferencia_de_caja", "id_user", "suma")
        self.assertEqual({"sin_asignar": 10.0}, rango["por_empleado"])

    # === fotos del dia en curso + corrida frecuente =====================================

    def _foto(self, query, actor_project=PROYECTO_A):
        """La foto de `query` fechada en DIA, como {categoria: valor}."""
        filas = self._consulta(query, actor_project, desde=DIA.date(), hasta=DIA.date())
        self.assertTrue(all(fila[1] == DIA.date() for fila in filas))
        return {fila[0]: fila[2] for fila in filas}

    def test_pedidos_del_dia_separa_cobrado_entregado_sin_cobrar_y_en_curso_sin_borradores(self):
        q = kpis_restaurante.pedidos_del_dia_query
        self.assertEqual({"cobrado": 0, "entregado_sin_cobrar": 0, "en_curso": 0}, self._foto(q))
        self._orden(97001, [(1, 10)], enviada=DIA)                                    # cobrado
        self._orden(97002, [(1, 10)], enviada=DIA, estado="entregado")                # entregado sin cobrar
        for id_orden, estado in enumerate(("pedido", "en_preparacion", "listo_para_entrega"), 97003):
            self._orden(id_orden, [(1, 10)], enviada=DIA, estado=estado)              # en curso x3
        self._orden(97006, [(1, 10)], estado="borrador")                              # borrador: no es un pedido hecho
        self._orden(97007, [(1, 10)], enviada=DIA, borrada=datetime(2026, 9, 16))     # borrada
        self._orden(97008, [(1, 10)], enviada=DIA, proyecto=PROYECTO_B, mesero=None)  # otro restaurante
        foto = self._foto(q)
        self.assertEqual({"cobrado": 1, "entregado_sin_cobrar": 1, "en_curso": 3}, foto)
        self.assertEqual(5, sum(foto.values()), "la suma de las tres es el total de pedidos hechos")
        self.assertEqual(6, sum(self._foto(q, None).values()), "sin proyecto: se suma el otro restaurante")

    def test_pedidos_del_dia_cuenta_por_dia_de_envio_no_por_dia_de_cobro(self):
        self._orden(97001, [(1, 10)], enviada=DIA - timedelta(days=1), pagada=DIA)
        self.assertEqual({"cobrado": 0, "entregado_sin_cobrar": 0, "en_curso": 0}, self._foto(kpis_restaurante.pedidos_del_dia_query))

    def test_cuentas_sin_cobrar_suma_lo_entregado_de_cualquier_dia_y_sin_propina(self):
        q = kpis_restaurante.cuentas_sin_cobrar_query
        self.assertEqual({None: Decimal("0.00")}, self._foto(q))
        self._orden(97001, [(3, 50), (1, 100)], estado="entregado", propina=30)                 # 250
        self._orden(97002, [(2, 20)], estado="entregado", enviada=DIA - timedelta(days=3))       # 40, de hace 3 dias
        self._orden(97003, [(1, 999)], estado="listo_para_entrega")                              # aun no se entrega
        self._orden(97004, [(1, 999)])                                                           # cobrada
        self._orden(97005, [(1, 999)], estado="entregado", borrada=datetime(2026, 9, 16))        # borrada
        self._orden(97006, [(1, 7)], estado="entregado", proyecto=PROYECTO_B, mesero=None)
        self.assertEqual({None: Decimal("290.00")}, self._foto(q))
        self.assertEqual({None: Decimal("297.00")}, self._foto(q, None))

    def test_cobrar_una_cuenta_la_pasa_de_cuentas_sin_cobrar_a_ventas(self):
        self._orden(97001, [(1, 100)], estado="entregado")
        self.assertEqual(Decimal("100.00"), self._foto(kpis_restaurante.cuentas_sin_cobrar_query)[None])
        with transaction_context() as db:
            db.execute(update(RestaurantOrder).where(RestaurantOrder.id_restaurant_order == 97001)
                       .values(status="pagado", paid_at=DIA))
        self.assertEqual(Decimal("0.00"), self._foto(kpis_restaurante.cuentas_sin_cobrar_query)[None])
        self.assertEqual(Decimal("100.00"), self._ventas()[0][2])

    CERO = {"libre": 0, "ocupada_con_cuenta_pendiente": 0, "por_liberar": 0}

    def _mesas(self, **cuentas):
        return {**self.CERO, **cuentas}

    def test_una_visita_sin_ordenes_cuenta_como_ocupada_con_cuenta_pendiente(self):
        # setUp deja dos visitas activas (mesas 7 y 8), todavia sin ninguna orden.
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=2), self._foto(kpis_restaurante.mesas_ocupadas_query))

    def test_una_visita_con_una_orden_pagada_y_otra_sin_pagar_sigue_con_cuenta_pendiente(self):
        self._orden(97001, [(1, 100)], visita=VISITA_A)
        self._orden(97002, [(1, 50)], visita=VISITA_A, estado="entregado")
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=2), self._foto(kpis_restaurante.mesas_ocupadas_query))

    def test_un_borrador_vacio_se_ignora_no_retiene_la_mesa_ni_cuenta_como_orden(self):
        q = kpis_restaurante.mesas_ocupadas_query
        # Pagada + el lugar vacio de otro comensal: la mesa esta por liberar.
        self._orden(97001, [(1, 100)], visita=VISITA_A)
        self._orden(97002, [], visita=VISITA_A, estado="borrador")
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=1, por_liberar=1), self._foto(q))
        # Solo borradores vacios: es como una visita sin ordenes (ocupada, aun sin cuenta), no "por liberar".
        self._orden(97003, [], visita=VISITA_A2, estado="borrador")
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=1, por_liberar=1), self._foto(q))
        # En cambio un borrador CON partidas si es una cuenta en curso y retiene la mesa.
        self._orden(97004, [(1, 5)], visita=VISITA_A, estado="borrador")
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=2), self._foto(q))

    def test_pedidos_del_dia_ignora_los_borradores_vacios_y_con_partidas(self):
        q = kpis_restaurante.pedidos_del_dia_query
        self._orden(97001, [(1, 10)], enviada=DIA)
        self._orden(97002, [], estado="borrador", enviada=DIA)        # vacio: se ignora
        self._orden(97003, [(1, 10)], estado="borrador", enviada=DIA)  # aun no es un pedido hecho
        self.assertEqual({"cobrado": 1, "entregado_sin_cobrar": 0, "en_curso": 0}, self._foto(q))

    def test_una_visita_con_todas_sus_ordenes_pagadas_es_por_liberar_aunque_nadie_la_cerro(self):
        self._orden(97001, [(1, 100)], visita=VISITA_A)
        self._orden(97002, [(2, 50)], visita=VISITA_A)
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=1, por_liberar=1),
                         self._foto(kpis_restaurante.mesas_ocupadas_query))

    def test_una_orden_borrada_no_cuenta_ni_para_pagada_ni_para_pendiente(self):
        self._orden(97001, [(1, 100)], visita=VISITA_A)
        self._orden(97002, [(1, 50)], visita=VISITA_A, estado="entregado", borrada=datetime(2026, 9, 16))
        self.assertEqual(self._mesas(ocupada_con_cuenta_pendiente=1, por_liberar=1),
                         self._foto(kpis_restaurante.mesas_ocupadas_query))

    def test_una_mesa_sin_visita_activa_esta_libre_y_cerrar_la_visita_la_libera(self):
        q = kpis_restaurante.mesas_ocupadas_query
        with transaction_context() as db:
            db.add(RestaurantTable(id_restaurant_table=9703, id_proyect=PROYECTO_A, number=9, created_by=ADMIN_ID))
            db.add(RestaurantTable(id_restaurant_table=9704, id_proyect=PROYECTO_A, number=10, is_active=False, created_by=ADMIN_ID))
            db.add(RestaurantTable(id_restaurant_table=9705, id_proyect=PROYECTO_A, number=11, deletion_date=DIA, created_by=ADMIN_ID))
        self.assertEqual(self._mesas(libre=1, ocupada_con_cuenta_pendiente=2), self._foto(q))  # inactiva y borrada no cuentan
        self._orden(97001, [(1, 100)], visita=VISITA_A)
        self.assertEqual(self._mesas(libre=1, ocupada_con_cuenta_pendiente=1, por_liberar=1), self._foto(q))
        with transaction_context() as db:  # cobrar no libero la mesa; cerrar la visita si
            db.execute(update(RestaurantVisit).where(RestaurantVisit.id_restaurant_visit == VISITA_A)
                       .values(status="closed", closed_at=DIA))
        self.assertEqual(self._mesas(libre=2, ocupada_con_cuenta_pendiente=1), self._foto(q))

    def test_las_categorias_de_mesas_tienen_su_etiqueta_visible(self):
        kpi = KPI_POR_CLAVE["mesas_ocupadas"]
        self.assertEqual(
            {"libre": "Libre", "ocupada_con_cuenta_pendiente": "Ocupada con cuenta pendiente", "por_liberar": "Pagada, aún ocupada"},
            kpi.etiquetas_categoria,
        )
        self.assertIn("cuando el mesero cierra la visita, no al cobrar", kpi.descripcion)
        self.assertIn("seguirá apareciendo como «Pagada, aún ocupada»", kpi.descripcion)

    def test_las_categorias_de_pedidos_tienen_su_etiqueta_visible(self):
        kpi = KPI_POR_CLAVE["pedidos_del_dia"]
        self.assertEqual(
            {"cobrado": "Cobrado", "entregado_sin_cobrar": "Entregado sin cobrar", "en_curso": "En curso"},
            kpi.etiquetas_categoria,
        )
        self.assertEqual(set(kpi.orden_categorias), set(kpi.etiquetas_categoria))

    def test_las_mesas_de_un_restaurante_no_cuentan_en_otro(self):
        self.assertEqual({"libre": 0, "ocupada_con_cuenta_pendiente": 0, "por_liberar": 0},
                         self._foto(kpis_restaurante.mesas_ocupadas_query, PROYECTO_B))

    def test_las_tres_fotos_son_ultimo_con_dimension_estado_y_colores_fijos(self):
        for clave, categorias in (("pedidos_del_dia", ("cobrado", "entregado_sin_cobrar", "en_curso")),
                                  ("mesas_ocupadas", ("libre", "ocupada_con_cuenta_pendiente", "por_liberar"))):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("ultimo", kpi.agregacion)
            self.assertEqual(("estado",), kpi.dimensiones)
            self.assertEqual(categorias, kpi.orden_categorias)
            self.assertEqual(set(categorias), set(kpi.colores_categoria))
            self.assertEqual("dona", kpi.grafica_default)
            self.assertFalse(kpi.sin_asignar, "sin_asignar no aplica: la categoria es texto fijo")
        self.assertEqual("ultimo", KPI_POR_CLAVE["cuentas_sin_cobrar"].agregacion)
        self.assertEqual("moneda", KPI_POR_CLAVE["cuentas_sin_cobrar"].unidad)

    def test_la_foto_llega_al_dashboard_con_sus_tres_categorias_aunque_valgan_cero(self):
        self._orden(97001, [(1, 10)], enviada=DIA, estado="entregado")
        kpis = tuple(k for k in definiciones() if k.clave in ("pedidos_del_dia", "mesas_ocupadas"))
        ids = self._registrar(kpis)
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", kpis):
            tasks_kpis.recalcular_kpi_snapshots_rango(DIA.date(), DIA.date())  # la foto de ese dia
        pedidos = self._rango(ids, "pedidos_del_dia", "estado", "ultimo")
        mesas = self._rango(ids, "mesas_ocupadas", "estado", "ultimo")
        self.assertEqual({"cobrado": 0.0, "entregado_sin_cobrar": 1.0, "en_curso": 0.0}, pedidos["por_empleado"])
        self.assertEqual({"libre": 0.0, "ocupada_con_cuenta_pendiente": 2.0, "por_liberar": 0.0}, mesas["por_empleado"])

    # --- corrida frecuente ---------------------------------------------------------

    def _registrar(self, kpis):
        ids, creadas = {}, []
        with transaction_context() as db:
            for kpi in kpis:
                fila = db.scalar(select(KpiDefinition).where(KpiDefinition.clave == kpi.clave))
                if fila is None:
                    fila = KpiDefinition(clave=kpi.clave, etiqueta=kpi.etiqueta, modulo=kpi.modulo,
                                         dimensiones=list(kpi.dimensiones), unidad=kpi.unidad)
                    db.add(fila)
                    db.flush()
                    creadas.append(fila.id_kpi_definition)
                ids[kpi.clave] = fila.id_kpi_definition
        self.addCleanup(self._borrar_definiciones, ids, creadas)
        return ids

    def _hoy(self):
        # La corrida frecuente fecha en el dia del NEGOCIO (`hoy_negocio`); la nocturna sigue con `date.today()`.
        falso = mock.MagicMock(wraps=date)
        falso.today.return_value = DIA.date()
        pila = contextlib.ExitStack()
        pila.enter_context(mock.patch.object(tasks_kpis, "date", falso))
        pila.enter_context(mock.patch.object(tasks_kpis, "hoy_negocio", return_value=DIA.date()))
        return pila

    def test_la_corrida_frecuente_solo_toca_restaurante_y_pos_y_solo_el_dia_de_hoy(self):
        ajeno = copy.copy(KPI_REGISTRY[0])
        self.assertNotIn(ajeno.modulo, frecuencia.MODULOS_FRECUENTES)
        ajeno.query_builder = mock.Mock(return_value=[])
        kpis = tuple(definiciones()) + (ajeno,)
        ids = self._registrar(kpis)
        self._orden(97001, [(1, 100)], pagada=DIA)                       # hoy
        self._orden(97002, [(1, 40)], pagada=DIA - timedelta(days=2))    # antier: la frecuente no lo recalcula
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", kpis), self._hoy():
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual(DIA.date().isoformat(), resultado["fecha_inicio"])
        self.assertEqual(DIA.date().isoformat(), resultado["fecha_fin"])
        ajeno.query_builder.assert_not_called()
        with transaction_context() as db:
            periodos = set(db.scalars(select(KpiSnapshot.periodo).where(
                KpiSnapshot.id_kpi_definition == ids["ventas_restaurante"])))
        self.assertEqual({DIA.date()}, periodos)

    def test_la_corrida_nocturna_sigue_recalculando_todos_los_modulos_con_su_ventana_de_7_dias(self):
        ajeno = copy.copy(KPI_REGISTRY[0])
        ajeno.query_builder = mock.Mock(return_value=[])
        kpis = tuple(definiciones()) + (ajeno,)
        ids = self._registrar(kpis)
        self._orden(97001, [(1, 100)], pagada=DIA)
        self._orden(97002, [(1, 40)], pagada=DIA - timedelta(days=2))
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", kpis), self._hoy():
            resultado = tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual((DIA.date() - timedelta(days=6)).isoformat(), resultado["fecha_inicio"])
        ajeno.query_builder.assert_called()
        with transaction_context() as db:
            periodos = set(db.scalars(select(KpiSnapshot.periodo).where(
                KpiSnapshot.id_kpi_definition == ids["ventas_restaurante"])))
        self.assertEqual({DIA.date(), DIA.date() - timedelta(days=2)}, periodos)

    def _valor_de_la_foto(self, id_definicion, periodo, categoria=None):
        with transaction_context() as db:
            filas = db.execute(select(KpiSnapshot.dimension_key, KpiSnapshot.valor).where(
                KpiSnapshot.id_kpi_definition == id_definicion, KpiSnapshot.periodo == periodo,
                KpiSnapshot.dimension_key["id_proyect"].as_integer() == PROYECTO_A)).all()
        return {(clave or {}).get("estado"): float(valor) for clave, valor in filas}

    def test_la_corrida_nocturna_no_sobrescribe_las_fotos_de_dias_anteriores(self):
        # Las fotos (agregacion "ultimo") solo se escriben en la fecha de la corrida: la nocturna recorre una ventana
        # de 7 dias, pero una foto de ayer es lo que ERA ayer y no debe reescribirse con el estado de hoy.
        kpis = tuple(k for k in definiciones() if k.clave in ("mesas_ocupadas", "cuentas_sin_cobrar", "pedidos_del_dia"))
        ids = self._registrar(kpis)
        ayer = DIA.date() - timedelta(days=1)
        self._orden(97001, [(1, 100)], estado="entregado", enviada=DIA - timedelta(days=1))
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", kpis):
            tasks_kpis.recalcular_kpi_snapshots_rango(ayer, ayer)           # la foto de ayer
        self.assertEqual({None: 100.0}, self._valor_de_la_foto(ids["cuentas_sin_cobrar"], ayer))
        self.assertEqual(1.0, self._valor_de_la_foto(ids["pedidos_del_dia"], ayer)["entregado_sin_cobrar"])
        mesas_ayer = self._valor_de_la_foto(ids["mesas_ocupadas"], ayer)
        self._orden(97002, [(1, 50)], estado="entregado", enviada=DIA)    # hoy cambia el estado
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", kpis), self._hoy():
            tasks_kpis.recalculate_kpi_snapshots()                           # nocturna: ventana de 7 dias
        self.assertEqual({None: 100.0}, self._valor_de_la_foto(ids["cuentas_sin_cobrar"], ayer), "ayer no cambia")
        self.assertEqual(mesas_ayer, self._valor_de_la_foto(ids["mesas_ocupadas"], ayer))
        self.assertEqual(1.0, self._valor_de_la_foto(ids["pedidos_del_dia"], ayer)["entregado_sin_cobrar"])
        self.assertEqual({None: 150.0}, self._valor_de_la_foto(ids["cuentas_sin_cobrar"], DIA.date()), "hoy si")
        self.assertEqual(1.0, self._valor_de_la_foto(ids["pedidos_del_dia"], DIA.date())["entregado_sin_cobrar"])

    def test_el_intervalo_es_una_constante_de_5_minutos_en_el_beat(self):
        self.assertEqual(5, frecuencia.INTERVALO_MINUTOS_POR_OMISION)
        with mock.patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop(frecuencia.INTERVALO_ENV, None)
            self.assertEqual(5, frecuencia.intervalo_minutos())
        for crudo, esperado in (("10", 10), ("0", 5), ("999", 5), ("x", 5), ("", 5)):
            with mock.patch.dict("os.environ", {frecuencia.INTERVALO_ENV: crudo}):
                self.assertEqual(esperado, frecuencia.intervalo_minutos(), crudo)
        entrada = BEAT_SCHEDULE["recalculate-kpi-snapshots-frecuentes"]
        self.assertEqual("app.jobs.tasks_kpis.recalculate_kpi_snapshots_frecuentes", entrada["task"])
        self.assertEqual(timedelta(minutes=5), entrada["schedule"])
        self.assertEqual("app.jobs.tasks_kpis.recalculate_kpi_snapshots", BEAT_SCHEDULE["recalculate-kpi-snapshots-nightly"]["task"])

    def test_los_modulos_frecuentes_existen_en_el_registro_de_modulos(self):
        self.assertEqual([], [m for m in frecuencia.MODULOS_FRECUENTES if m not in MODULO_POR_CLAVE])

    # --- zona horaria: el dia es el del negocio, no el de UTC ----------------------------------
    # La base guarda UTC; America/Mexico_City es UTC-6 todo el ano. 18:10 local = 00:10 UTC del dia siguiente.

    def test_un_cobro_a_las_18_10_locales_queda_en_el_mismo_dia_local(self):
        self._orden(97001, [(1, 100)], pagada=datetime(2026, 9, 16, 0, 10))   # 15-sep 18:10 local
        self.assertEqual([(None, date(2026, 9, 15), Decimal("100"))], self._ventas())

    def test_un_cobro_a_las_23_50_y_otro_a_las_00_10_locales_quedan_en_dias_distintos(self):
        self._orden(97001, [(1, 100)], pagada=datetime(2026, 9, 16, 5, 50))   # 15-sep 23:50 local
        self._orden(97002, [(1, 40)], pagada=datetime(2026, 9, 16, 6, 10))    # 16-sep 00:10 local
        self.assertEqual(
            [(None, date(2026, 9, 15), Decimal("100")), (None, date(2026, 9, 16), Decimal("40"))],
            self._ventas())

    def test_el_dia_local_tambien_rige_envio_entrega_y_cierre_de_caja_y_pedidos_del_dia(self):
        tarde = datetime(2026, 9, 16, 3, 0)   # 15-sep 21:00 local
        self._orden(97001, [(1, 10)], enviada=tarde, lista=tarde - timedelta(minutes=10), entregada=tarde)
        self._sesion(97001, 5, cerrada=tarde)
        self.assertEqual([(MESERO_ROSA, date(2026, 9, 15), 1)], [tuple(f) for f in self._consulta(kpis_restaurante.servicios_por_mesero_query)])
        self.assertEqual(date(2026, 9, 15), self._consulta(kpis_restaurante.tiempo_de_entrega_query)[0][1])
        self.assertEqual(date(2026, 9, 15), self._consulta(kpis_restaurante.diferencia_de_caja_query)[0][1])
        self.assertEqual(1, self._foto(kpis_restaurante.pedidos_del_dia_query)["cobrado"])

    # --- las banderas -----------------------------------------------------------

    def test_sin_asignar_esta_encendida_en_los_nuevos_con_entidad_opcional_y_apagada_en_los_24_originales(self):
        from app.kpis.registry import KPI_REGISTRY

        originales = KPI_REGISTRY[:24]
        self.assertEqual(24, len(originales))
        self.assertEqual([], [k.clave for k in originales if k.sin_asignar])
        encendidas = {k.clave for k in definiciones() if k.sin_asignar}
        self.assertEqual(
            {"ventas_por_mesero", "platillos_mas_vendidos", "frecuencia_por_platillo", "top_mesas",
             "servicios_por_mesero", "diferencia_de_caja"},
            encendidas,
        )


if __name__ == "__main__":
    unittest.main()
