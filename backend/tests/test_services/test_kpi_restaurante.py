from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest import mock

from sqlalchemy import delete, select

from app.jobs import tasks_kpis
from app.kpis.registry import KPI_POR_CLAVE
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
        self._orden(97001, [(1, 10)], pagada=datetime(2026, 9, 1, 0, 5))
        self._orden(97002, [(1, 20)], pagada=datetime(2026, 9, 30, 23, 55))
        self._orden(97003, [(1, 400)], pagada=datetime(2026, 8, 31, 23, 59))
        self._orden(97004, [(1, 800)], pagada=datetime(2026, 10, 1, 0, 0))
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

    def test_diferencia_de_caja_suma_con_signo_las_sesiones_cerradas_por_cajero(self):
        self._sesion(97001, Decimal("-50.00"), cierra=CAJERO_A)
        self._sesion(97002, Decimal("20.00"), cierra=CAJERO_A)
        self._sesion(97003, Decimal("5.00"), cierra=CAJERO_B)
        self._sesion(97004, None, estado="open")  # abierta: no cuenta
        filas = {fila[0]: fila[2] for fila in self._consulta(kpis_restaurante.diferencia_de_caja_query)}
        self.assertEqual({CAJERO_A: Decimal("-30.00"), CAJERO_B: Decimal("5.00")}, filas)

    def test_diferencia_de_caja_esta_por_confirmar_neutral_y_sin_sembrar_a_ningun_rol(self):
        from scripts.seed_kpi_permissions import ASIGNACIONES

        kpi = KPI_POR_CLAVE["diferencia_de_caja"]
        self.assertEqual("neutral", kpi.direccion)
        self.assertIn("Por confirmar", kpi.descripcion)
        asignadas = {clave for perfil in ASIGNACIONES.values() for rol in perfil for clave in rol.kpis}
        self.assertFalse(asignadas & {k.clave for k in definiciones()}, "ningun KPI de restaurante se siembra a un rol")

    def test_una_sesion_sin_cajero_sale_como_sin_asignar(self):
        self._sesion(97001, Decimal("-10.00"), cierra=None)
        ids = self._correr_job("diferencia_de_caja")
        rango = self._rango(ids, "diferencia_de_caja", "id_user", "suma")
        self.assertEqual({"sin_asignar": -10.0}, rango["por_empleado"])

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
