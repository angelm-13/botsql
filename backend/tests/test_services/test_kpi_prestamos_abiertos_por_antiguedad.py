"""`prestamos_abiertos_por_antiguedad`: renglones prestados sin devolver, por dias desde el vale.

Corre solo contra PostgreSQL (usa `generate_series`). Cada prueba compara contra una LINEA BASE
medida antes de sembrar su fixture, asi que no depende de que la base no traiga ya vales (datos
demo, una copia de la base local): solo cuenta lo que ella misma agrega.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.kpis.registry import (
    ANTIGUEDAD_CATEGORIAS, ANTIGUEDAD_COLORES, KPI_POR_CLAVE, prestamos_abiertos_por_antiguedad_query,
)
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context
from app.services.warehouse_voucher_service import CIERRE_SENTINELA

ADMIN_ID = 1
# IDs propios (950+) para no chocar con los fixtures de los demas archivos de KPI.
EMPLEADO = 950
TIPO_NORMAL, TIPO_DESTRUCCION, TIPO_EXTRAVIADO, TIPO_DANADO = 950, 951, 952, 953
TIPOS = [TIPO_NORMAL, TIPO_DESTRUCCION, TIPO_EXTRAVIADO, TIPO_DANADO]
LOCATION_TYPE = LOCATION = BRAND = FAMILIA = UNIT = MATERIAL = INVOICE = PRODUCTO = 950

HOY = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
ID_VALE = 9500
ID_RENGLON = 95000


def _foto(session, desde=None, hasta=None):
    desde = desde or HOY.date()
    hasta = hasta or HOY.date()
    filas = prestamos_abiertos_por_antiguedad_query(session, desde, hasta, {}, None)
    return {(fecha, categoria): valor for categoria, fecha, valor in filas}


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class PrestamosAbiertosPorAntiguedadTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        self._siguiente_vale = ID_VALE
        self._siguiente_renglon = ID_RENGLON
        with transaction_context() as db:
            # Cubre los dias que miran las pruebas (hoy y hasta 15 atras).
            self.base = _foto(db, HOY.date() - timedelta(days=15), HOY.date())
        with transaction_context() as db:
            db.add(User(id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado 950", id_permission=1,
                        id_proyect=1, id_status=1, supervisor=ADMIN_ID, user_type="employee", is_employee=True,
                        username="kpi-prestamos-antiguedad-test"))
            db.add_all([
                IncidentType(id_incident_type=TIPO_NORMAL, incident_type_description="Vale normal", created_by=ADMIN_ID),
                IncidentType(id_incident_type=TIPO_DESTRUCCION, incident_type_description="Destruccion", created_by=ADMIN_ID),
                IncidentType(id_incident_type=TIPO_EXTRAVIADO, incident_type_description="Extraviado", created_by=ADMIN_ID),
                IncidentType(id_incident_type=TIPO_DANADO, incident_type_description="Dañado", created_by=ADMIN_ID),
                LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI test", is_warehouse=True, created_by=ADMIN_ID),
                Brand(id_brand=BRAND, brand_description="KPI test", created_by=ADMIN_ID),
                ProductFamily(id_product_family=FAMILIA, product_family_description="KPI test", created_by=ADMIN_ID),
                Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID),
            ])
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI test", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI test", id_unit=UNIT, id_brand=BRAND,
                            id_product_family=FAMILIA, created_by=ADMIN_ID))
            db.add(Invoice(id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1, id_proyect=1,
                           id_status=1, tax_certification_supplier=1, apply_tax=False, invoice_status="pendiente",
                           created_by=ADMIN_ID))
            db.flush()
            db.add(Product(id_product=PRODUCTO, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                           is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
                           descripcion="Taladro", product_code="ANT-001"))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product == PRODUCTO))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(TIPOS)))
            db.execute(delete(Product).where(Product.id_product == PRODUCTO))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == FAMILIA))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_(TIPOS)))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _vale(self, dias_atras, *, tipo=TIPO_NORMAL, direction="salida", close_date=None,
              borrado=False, sin_fecha=False):
        """Un vale con UN renglon, abierto hace `dias_atras` dias."""
        id_vale, id_renglon = self._siguiente_vale, self._siguiente_renglon
        self._siguiente_vale += 1
        self._siguiente_renglon += 1
        with transaction_context() as db:
            db.add(Incident(
                id_incident=id_vale, id_incident_type=tipo, id_user=EMPLEADO, incident_status="abierta",
                incident_date=None if sin_fecha else HOY - timedelta(days=dias_atras), created_by=EMPLEADO,
            ))
            db.flush()
            db.add(NmIncidentProduct(
                id_nm_incident_product=id_renglon, id_incident=id_vale, id_product=PRODUCTO, quantity=1,
                direction=direction, close_date=close_date, created_by=ADMIN_ID,
                deletion_date=HOY if borrado else None,
            ))

    def _delta(self, desde=None, hasta=None):
        """Lo que la fixture agrego a la foto, por (fecha, categoria), sin ceros."""
        with transaction_context() as db:
            ahora = _foto(db, desde, hasta)
        return {llave: valor - self.base.get(llave, 0) for llave, valor in ahora.items()
                if valor - self.base.get(llave, 0)}

    def _hoy(self, delta):
        return {categoria: valor for (fecha, categoria), valor in delta.items() if fecha == HOY.date()}

    # --- bordes de las categorias -------------------------------------------------------
    def test_bordes_de_cada_categoria(self):
        for dias in (0, 30, 31, 60, 61, 90, 91, 400):
            self._vale(dias)
        self.assertEqual({"0-30": 2, "31-60": 2, "61-90": 2, "+90": 2}, self._hoy(self._delta()))

    def test_30_31_60_61_90_91_uno_por_uno(self):
        esperado = {30: "0-30", 31: "31-60", 60: "31-60", 61: "61-90", 90: "61-90", 91: "+90"}
        for dias, categoria in esperado.items():
            with self.subTest(dias=dias):
                self._limpiar_renglones()
                self._vale(dias)
                self.assertEqual({categoria: 1}, self._hoy(self._delta()))

    def _limpiar_renglones(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product == PRODUCTO))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(TIPOS)))

    # --- que cuenta como prestamo abierto -----------------------------------------------
    def test_sentinel_y_nulo_cuentan_como_abiertos(self):
        self._vale(10, close_date=None)
        self._vale(10, close_date=CIERRE_SENTINELA)
        self.assertEqual({"0-30": 2}, self._hoy(self._delta()))

    def test_danado_cuenta_y_las_bajas_no(self):
        self._vale(10, tipo=TIPO_DANADO)       # dañado: sigue prestado, cuenta
        self._vale(10, tipo=TIPO_DESTRUCCION)  # baja: no esta con nadie
        self._vale(10, tipo=TIPO_EXTRAVIADO)   # baja
        self.assertEqual({"0-30": 1}, self._hoy(self._delta()))

    def test_cerrado_entrada_borrado_y_sin_fecha_no_cuentan(self):
        self._vale(10, close_date=HOY - timedelta(days=1))   # ya devuelto
        self._vale(10, direction="entrada")                   # una entrada no es prestamo
        self._vale(10, borrado=True)                          # renglon borrado
        self._vale(10, sin_fecha=True)                        # vale sin fecha: no hay antiguedad
        self.assertEqual({}, self._hoy(self._delta()))

    # --- reconstruccion de dias pasados ---------------------------------------------------
    def test_reconstruye_la_antiguedad_y_lo_abierto_de_cada_dia(self):
        hoy = HOY.date()
        hace_10 = hoy - timedelta(days=10)
        self._vale(40)                                        # hace 10 dias tenia 30 (0-30); hoy tiene 40 (31-60)
        self._vale(40, close_date=HOY - timedelta(days=5))    # abierto hace 10 dias; cerrado hace 5
        self._vale(3)                                         # no existia hace 10 dias
        self._vale(20, close_date=HOY - timedelta(days=10))   # cerrado EN ese dia: ya no cuenta ese dia
        delta = self._delta(hace_10, hoy)
        self.assertEqual({"0-30": 2}, {c: v for (f, c), v in delta.items() if f == hace_10})
        self.assertEqual({"31-60": 1, "0-30": 1}, {c: v for (f, c), v in delta.items() if f == hoy})
        hace_6 = hoy - timedelta(days=6)
        # hace 6 dias: los dos de hace 40 (cada uno con 34 dias) seguian abiertos -el cerrado hace 5 aun no
        # se cerraba-, el de hace 3 aun no existia y el cerrado hace 10 ya estaba cerrado.
        self.assertEqual({"31-60": 2}, {c: v for (f, c), v in delta.items() if f == hace_6})

    def test_siempre_trae_las_cuatro_categorias_de_cada_dia_aunque_sea_con_cero(self):
        with transaction_context() as db:
            filas = prestamos_abiertos_por_antiguedad_query(db, HOY.date() - timedelta(days=2), HOY.date(), {}, None)
        self.assertEqual(3 * len(ANTIGUEDAD_CATEGORIAS), len(filas))
        self.assertEqual(set(ANTIGUEDAD_CATEGORIAS), {categoria for categoria, _, _ in filas})

    # --- metadatos -------------------------------------------------------------------------
    def test_metadatos_del_registry(self):
        kpi = KPI_POR_CLAVE["prestamos_abiertos_por_antiguedad"]
        self.assertEqual(("estado",), kpi.dimensiones)
        self.assertEqual("Antigüedad", kpi.etiqueta_dimension)
        self.assertEqual("ultimo", kpi.agregacion)
        self.assertEqual("snapshot", kpi.modo)
        self.assertFalse(kpi.alcance_proyecto)
        self.assertEqual("barras", kpi.grafica_default)
        self.assertEqual(set(ANTIGUEDAD_CATEGORIAS), set(kpi.colores_categoria))
        self.assertEqual(ANTIGUEDAD_COLORES, kpi.colores_categoria)


if __name__ == "__main__":
    unittest.main()
