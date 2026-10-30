"""`perdidas_por_familia`: piezas destruidas, extraviadas o dañadas, por familia de producto.

Solo PostgreSQL. Cada prueba compara contra una LINEA BASE medida antes de sembrar su fixture, asi
que no depende de que la base no traiga ya vales (datos demo, una copia de la base local).
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select

from app.kpis.registry import FAMILIA_SIN_ASIGNAR, KPI_POR_CLAVE, perdidas_por_familia_query
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.session import engine, transaction_context
from app.routes.kpi import _etiquetas_de_familias, _totales

ADMIN_ID = 1
# IDs propios (940+) para no chocar con los fixtures de los demas archivos de KPI.
EMPLEADO = 940
T_NORMAL, T_DESTRUCCION, T_EXTRAVIADO, T_DANADO, T_REPARACION, T_DESTRUCCION_ACENTO = 940, 941, 942, 943, 944, 945
TIPOS = [T_NORMAL, T_DESTRUCCION, T_EXTRAVIADO, T_DANADO, T_REPARACION, T_DESTRUCCION_ACENTO]
FAM_A, FAM_B = 940, 941
LOCATION_TYPE = LOCATION = BRAND = UNIT = MATERIAL = INVOICE = 940
FAM_MATERIAL = 949  # la familia del MATERIAL: no debe aparecer (la que cuenta es la del producto)
P_A, P_B, P_SIN = 940, 941, 942
PRODUCTOS = [P_A, P_B, P_SIN]
HOY = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
HOY_D = HOY.date()


def _foto(session, desde, hasta):
    filas = perdidas_por_familia_query(session, desde, hasta, {}, None)
    return {(fecha, familia): piezas for familia, fecha, piezas in filas}


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class PerdidasPorFamiliaQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        self._vale_n = 9400
        self._renglon_n = 94000
        self.desde = HOY_D - timedelta(days=10)
        with transaction_context() as db:
            self.base = _foto(db, self.desde, HOY_D)
        with transaction_context() as db:
            db.add(User(id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado 940", id_permission=1, id_proyect=1,
                        id_status=1, supervisor=ADMIN_ID, user_type="employee", is_employee=True,
                        username="kpi-perdidas-familia-test"))
            db.add_all([
                IncidentType(id_incident_type=T_NORMAL, incident_type_description="Vale normal", created_by=ADMIN_ID),
                IncidentType(id_incident_type=T_DESTRUCCION, incident_type_description="Destruccion", created_by=ADMIN_ID),
                IncidentType(id_incident_type=T_EXTRAVIADO, incident_type_description="Extraviado", created_by=ADMIN_ID),
                IncidentType(id_incident_type=T_DANADO, incident_type_description="Dañado", created_by=ADMIN_ID),
                IncidentType(id_incident_type=T_REPARACION, incident_type_description="Reparacion", created_by=ADMIN_ID),
                IncidentType(id_incident_type=T_DESTRUCCION_ACENTO, incident_type_description="  Destrucción ", created_by=ADMIN_ID),
                LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI test", is_warehouse=True, created_by=ADMIN_ID),
                Brand(id_brand=BRAND, brand_description="KPI test", created_by=ADMIN_ID),
                ProductFamily(id_product_family=FAM_A, product_family_description="Familia A", created_by=ADMIN_ID),
                ProductFamily(id_product_family=FAM_B, product_family_description="Familia B", created_by=ADMIN_ID),
                ProductFamily(id_product_family=FAM_MATERIAL, product_family_description="Del material", created_by=ADMIN_ID),
                Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID),
            ])
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI test", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI test", id_unit=UNIT, id_brand=BRAND,
                            id_product_family=FAM_MATERIAL, created_by=ADMIN_ID))
            db.add(Invoice(id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1, id_proyect=1,
                           id_status=1, tax_certification_supplier=1, apply_tax=False, invoice_status="pendiente",
                           created_by=ADMIN_ID))
            db.flush()
            for id_product, familia in ((P_A, FAM_A), (P_B, FAM_B), (P_SIN, None)):
                db.add(Product(id_product=id_product, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                               is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
                               descripcion=f"Producto {id_product}", product_code=f"PF-{id_product}", id_familia=familia))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product.in_(PRODUCTOS)))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(TIPOS)))
            db.execute(delete(Product).where(Product.id_product.in_(PRODUCTOS)))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family.in_([FAM_A, FAM_B, FAM_MATERIAL])))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_(TIPOS)))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _renglon(self, producto, tipo, cantidad, dias_atras=0, *, direction="salida", borrado=False):
        id_vale, id_renglon = self._vale_n, self._renglon_n
        self._vale_n += 1
        self._renglon_n += 1
        with transaction_context() as db:
            db.add(Incident(id_incident=id_vale, id_incident_type=tipo, id_user=EMPLEADO, incident_status="abierta",
                            incident_date=HOY - timedelta(days=dias_atras), created_by=EMPLEADO))
            db.flush()
            db.add(NmIncidentProduct(id_nm_incident_product=id_renglon, id_incident=id_vale, id_product=producto,
                                     quantity=cantidad, direction=direction, created_by=ADMIN_ID,
                                     deletion_date=HOY if borrado else None))

    def _delta(self):
        with transaction_context() as db:
            ahora = _foto(db, self.desde, HOY_D)
        return {llave: valor - self.base.get(llave, 0) for llave, valor in ahora.items()
                if valor - self.base.get(llave, 0)}

    def test_suma_piezas_por_familia_y_por_dia_de_destruccion_extravio_y_danado(self):
        self._renglon(P_A, T_DESTRUCCION, 3)                 # familia A, hoy
        self._renglon(P_A, T_EXTRAVIADO, 2, dias_atras=1)    # familia A, ayer
        self._renglon(P_B, T_DANADO, 4)                      # familia B, hoy
        self._renglon(P_B, T_DANADO, 1, direction="entrada") # la direccion no importa: lo define el tipo
        self.assertEqual({
            (HOY_D, FAM_A): 3,
            (HOY_D - timedelta(days=1), FAM_A): 2,
            (HOY_D, FAM_B): 5,
        }, self._delta())

    def test_cuenta_piezas_no_renglones(self):
        self._renglon(P_A, T_DESTRUCCION, 7)
        self._renglon(P_A, T_DESTRUCCION, 1)
        self.assertEqual({(HOY_D, FAM_A): 8}, self._delta())  # 2 renglones, 8 piezas

    def test_reparacion_y_vales_normales_no_son_perdida(self):
        self._renglon(P_A, T_REPARACION, 9)   # una herramienta en reparacion no esta perdida
        self._renglon(P_A, T_NORMAL, 7)       # un prestamo normal tampoco
        self.assertEqual({}, self._delta())

    def test_el_tipo_se_reconoce_sin_acentos_ni_espacios(self):
        self._renglon(P_B, T_DESTRUCCION_ACENTO, 2)  # "  Destrucción " (con acento y espacios)
        self.assertEqual({(HOY_D, FAM_B): 2}, self._delta())

    def test_producto_sin_familia_se_agrupa_como_sin_familia_y_no_desaparece(self):
        self._renglon(P_SIN, T_EXTRAVIADO, 5)
        self.assertEqual({(HOY_D, FAMILIA_SIN_ASIGNAR): 5}, self._delta())

    def test_usa_la_familia_del_producto_no_la_del_material(self):
        # El material de los 3 productos es de la familia "Del material" (FAM_MATERIAL): no debe aparecer.
        self._renglon(P_A, T_DESTRUCCION, 1)
        self.assertNotIn(FAM_MATERIAL, {familia for _, familia in self._delta()})

    def test_borrados_y_fuera_de_rango_no_cuentan(self):
        self._renglon(P_A, T_DESTRUCCION, 6, borrado=True)
        self._renglon(P_A, T_DESTRUCCION, 6, dias_atras=11)  # antes del rango
        self.assertEqual({}, self._delta())

    def test_no_corta_el_top_en_la_consulta(self):
        # El corte a 10 se hace al sumar el rango, no aqui: toda familia con perdidas se guarda.
        self._renglon(P_A, T_DESTRUCCION, 1)
        self._renglon(P_B, T_DESTRUCCION, 1)
        self._renglon(P_SIN, T_DESTRUCCION, 1)
        self.assertEqual({FAM_A, FAM_B, FAMILIA_SIN_ASIGNAR}, {familia for _, familia in self._delta()})

    def test_metadatos_del_registry(self):
        kpi = KPI_POR_CLAVE["perdidas_por_familia"]
        self.assertEqual(("familia",), kpi.dimensiones)
        self.assertEqual("Familia", kpi.etiqueta_dimension)
        self.assertEqual("suma", kpi.agregacion)
        self.assertEqual("piezas", kpi.unidad)
        self.assertEqual(10, kpi.limite_categorias)
        self.assertEqual(("barras",), kpi.graficas_permitidas)
        self.assertFalse(kpi.alcance_proyecto)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class PerdidasPorFamiliaTopTest(unittest.TestCase):
    """El corte a 10 al SUMAR el rango y los nombres de las familias."""

    CLAVE = "zz_prueba_perdidas_por_familia"

    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            definicion = KpiDefinition(clave=self.CLAVE, etiqueta="Prueba", modulo="operaciones",
                                       dimensiones=["familia"], unidad="piezas")
            db.add(definicion)
            db.flush()
            self.id_kpi = definicion.id_kpi_definition
            # 12 familias con 1..12 piezas el dia A; la familia 1 suma otras 100 el dia B.
            for familia in range(1, 13):
                db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_familia": familia},
                                   periodo=date(2026, 9, 1), valor=familia))
            db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_familia": 1},
                               periodo=date(2026, 9, 2), valor=100))
            db.add_all([
                ProductFamily(id_product_family=FAM_A, product_family_description="Familia A", created_by=ADMIN_ID),
            ])

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            ids = db.scalars(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == self.CLAVE)).all()
            if ids:
                db.execute(delete(KpiSnapshot).where(KpiSnapshot.id_kpi_definition.in_(ids)))
                db.execute(delete(KpiDefinition).where(KpiDefinition.id_kpi_definition.in_(ids)))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == FAM_A))

    def _sumar(self, limite):
        with transaction_context() as db:
            return _totales(db, self.id_kpi, date(2026, 9, 1), date(2026, 9, 2), None, None, "id_familia", "suma",
                            False, limite)

    def test_el_corte_a_10_se_hace_al_sumar_el_rango_y_deja_las_mayores(self):
        rango = self._sumar(10)
        # Familia 1: 1 + 100 = 101 (la mayor, aunque el dia A fuera la menor); luego 12, 11, ..., 4.
        self.assertEqual(
            {"1": 101.0, "12": 12.0, "11": 11.0, "10": 10.0, "9": 9.0, "8": 8.0, "7": 7.0, "6": 6.0, "5": 5.0, "4": 4.0},
            rango["por_empleado"],
        )
        self.assertEqual(10, len(rango["por_empleado"]))
        # Sin "Otros": las dos menores (2 y 3) simplemente no se muestran...
        self.assertNotIn("2", rango["por_empleado"])
        self.assertNotIn("3", rango["por_empleado"])
        # ...pero el total sigue siendo el de TODAS las familias (78 + 100).
        self.assertEqual(178.0, rango["total"])

    def test_sin_limite_trae_todas(self):
        rango = self._sumar(None)
        self.assertEqual(12, len(rango["por_empleado"]))

    def test_etiquetas_de_familias(self):
        rango = {"por_empleado": {str(FAM_A): 3.0, str(FAMILIA_SIN_ASIGNAR): 2.0, "99999": 1.0}}
        with transaction_context() as db:
            etiquetas = _etiquetas_de_familias(db, (rango, None))
        self.assertEqual({str(FAM_A): "Familia A", "0": "Sin familia", "99999": "#99999"}, etiquetas)


if __name__ == "__main__":
    unittest.main()
