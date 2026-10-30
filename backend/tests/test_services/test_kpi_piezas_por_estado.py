"""`piezas_por_estado`: foto de cuantas piezas hay en cada estado.

Corre solo contra PostgreSQL. Cada prueba compara contra una LINEA BASE medida antes de sembrar su
fixture (la base real ya trae piezas y vales): solo cuenta lo que ella misma agrega.

El KPI esta PENDIENTE DE CONCILIAR contra tyakxa-dev (ver el docstring de
`piezas_por_estado_query`): estas pruebas fijan la REGLA, no que los numeros de Adser cuadren.
"""

from __future__ import annotations

import csv
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, select

from app.kpis.registry import (
    KPI_POR_CLAVE, PIEZAS_CATEGORIAS, PIEZAS_COLORES, piezas_por_estado_query,
)
from app.models import (
    Brand, Incident, IncidentType, InventoryStatus, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context
from app.services.warehouse_voucher_service import CIERRE_SENTINELA

ADMIN_ID = 1
# IDs propios (960+) para no chocar con los fixtures de los demas archivos de KPI.
EMPLEADO = 960
TIPO_NORMAL, TIPO_DESTRUCCION, TIPO_EXTRAVIADO, TIPO_DANADO = 960, 961, 962, 963
TIPOS = [TIPO_NORMAL, TIPO_DESTRUCCION, TIPO_EXTRAVIADO, TIPO_DANADO]
LOCATION_TYPE = LOCATION = BRAND = FAMILIA = UNIT = MATERIAL = INVOICE = 960
PRIMER_PRODUCTO = 96000
PRIMER_VALE = 9600
PRIMER_RENGLON = 960000
CODIGOS = ("retirado", "extraviado", "danado", "en_reparacion", "activo")

HOY = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
MUESTRA = Path(__file__).resolve().parents[1] / "fixtures" / "estado_de_piezas_adser_muestra.csv"


def _foto(session):
    return {cat: valor for cat, _fecha, valor in piezas_por_estado_query(session, HOY.date(), HOY.date(), {}, None)}


def _total_de_piezas(session):
    return session.scalar(select(func.count()).select_from(Product).where(Product.deletion_date.is_(None)))


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class PiezasPorEstadoTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        self._sig_producto = PRIMER_PRODUCTO
        self._sig_vale = PRIMER_VALE
        self._sig_renglon = PRIMER_RENGLON
        with transaction_context() as db:
            self.base = _foto(db)
            self.base_total = _total_de_piezas(db)
        with transaction_context() as db:
            db.add(User(id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado 960", id_permission=1,
                        id_proyect=1, id_status=1, supervisor=ADMIN_ID, user_type="employee", is_employee=True,
                        username="kpi-piezas-por-estado-test"))
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
            # Estados de catalogo PROPIOS de la prueba (no se asume que la base traiga el catalogo).
            self.estado = {}
            for codigo in CODIGOS:
                fila = InventoryStatus(
                    inventory_status_code=codigo, inventory_status_description=f"KPI test {codigo}",
                    color="#000000", entity_scope="kpi_piezas_test", flow_scope="inventory",
                    id_department=1, id_minimum_level=1, is_active=True, is_terminal=False,
                    visible_to_other_departments=False, sort_order=10, created_by=ADMIN_ID)
                db.add(fila)
                db.flush()
                self.estado[codigo] = fila.id_inventory_status

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_nm_incident_product >= PRIMER_RENGLON))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(TIPOS)))
            db.execute(delete(Product).where(Product.id_product >= PRIMER_PRODUCTO, Product.id_product < PRIMER_PRODUCTO + 10000))
            db.execute(delete(InventoryStatus).where(InventoryStatus.entity_scope == "kpi_piezas_test"))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == FAMILIA))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_(TIPOS)))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    # --- fixtures -----------------------------------------------------------------------
    def _pieza(self, estado=None, *, borrada=False):
        id_product = self._sig_producto
        self._sig_producto += 1
        with transaction_context() as db:
            db.add(Product(
                id_product=id_product, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                is_directly_related_to_product_service=False, cantidad=1, created_by=ADMIN_ID,
                descripcion="Pieza", product_code=f"PZ-{id_product}",
                id_inventory_status=self.estado[estado] if estado else None,
                deletion_date=HOY if borrada else None,
            ))
        return id_product

    def _renglon(self, pieza, *, tipo=TIPO_NORMAL, direction="salida", close_date=None,
                 renglon_borrado=False, vale_borrado=False, sin_fecha=False):
        id_vale, id_renglon = self._sig_vale, self._sig_renglon
        self._sig_vale += 1
        self._sig_renglon += 1
        with transaction_context() as db:
            db.add(Incident(
                id_incident=id_vale, id_incident_type=tipo, id_user=EMPLEADO, incident_status="abierta",
                incident_date=None if sin_fecha else HOY - timedelta(days=3), created_by=EMPLEADO,
                deletion_date=HOY if vale_borrado else None,
            ))
            db.flush()
            db.add(NmIncidentProduct(
                id_nm_incident_product=id_renglon, id_incident=id_vale, id_product=pieza, quantity=1,
                direction=direction, close_date=close_date, created_by=ADMIN_ID,
                deletion_date=HOY if renglon_borrado else None,
            ))

    def _delta(self):
        with transaction_context() as db:
            ahora = _foto(db)
        return {cat: ahora[cat] - self.base[cat] for cat in PIEZAS_CATEGORIAS if ahora[cat] != self.base[cat]}

    # --- una pieza por categoria ---------------------------------------------------------
    def test_una_pieza_por_categoria(self):
        self._pieza("retirado")
        self._pieza("extraviado")
        self._pieza("danado")
        self._pieza("en_reparacion")
        self._renglon(self._pieza())          # prestada, sin estado
        self._pieza()                         # libre
        self.assertEqual({cat: 1 for cat in PIEZAS_CATEGORIAS}, self._delta())

    def test_siempre_regresa_las_seis_categorias_en_orden_y_fechadas_en_fecha_fin(self):
        with transaction_context() as db:
            filas = piezas_por_estado_query(db, HOY.date() - timedelta(days=5), HOY.date(), {}, None)
        self.assertEqual(list(PIEZAS_CATEGORIAS), [cat for cat, _f, _v in filas])
        self.assertEqual({HOY.date()}, {fecha for _c, fecha, _v in filas})

    # --- prioridad -----------------------------------------------------------------------
    def test_el_estado_gana_sobre_un_prestamo_abierto(self):
        for estado in ("retirado", "extraviado", "danado", "en_reparacion"):
            self._renglon(self._pieza(estado))
        self.assertEqual({"En reparación": 1, "Dañado": 1, "Extraviado": 1, "Destruccion": 1}, self._delta())

    def test_un_estado_sin_problema_cae_en_salida_o_entrada(self):
        self._renglon(self._pieza("activo"))
        self._pieza("activo")
        self.assertEqual({"Salida": 1, "Entrada": 1}, self._delta())

    # --- que cuenta como Salida ----------------------------------------------------------
    def test_dos_renglones_abiertos_de_la_misma_pieza_cuentan_una_vez(self):
        pieza = self._pieza()
        self._renglon(pieza)
        self._renglon(pieza)
        self.assertEqual({"Salida": 1}, self._delta())

    def test_el_centinela_de_adser_cuenta_como_abierto(self):
        self._renglon(self._pieza(), close_date=CIERRE_SENTINELA)
        self.assertEqual({"Salida": 1}, self._delta())

    def test_un_renglon_cerrado_ya_no_es_salida(self):
        self._renglon(self._pieza(), close_date=HOY - timedelta(days=1))
        self.assertEqual({"Entrada": 1}, self._delta())

    def test_un_renglon_de_entrada_no_es_salida(self):
        self._renglon(self._pieza(), direction="entrada")
        self.assertEqual({"Entrada": 1}, self._delta())

    def test_un_vale_de_baja_abierto_no_convierte_la_pieza_en_salida(self):
        self._renglon(self._pieza(), tipo=TIPO_DESTRUCCION)
        self._renglon(self._pieza(), tipo=TIPO_EXTRAVIADO)
        self.assertEqual({"Entrada": 2}, self._delta())

    def test_un_vale_de_danado_abierto_si_cuenta_como_prestamo(self):
        # Mismo criterio que `prestamos_abiertos_por_antiguedad` (decision de Alan, 2026-09-29).
        self._renglon(self._pieza(), tipo=TIPO_DANADO)
        self.assertEqual({"Salida": 1}, self._delta())

    def test_una_baja_junto_a_un_prestamo_normal_si_es_salida(self):
        pieza = self._pieza()
        self._renglon(pieza, tipo=TIPO_EXTRAVIADO)
        self._renglon(pieza)
        self.assertEqual({"Salida": 1}, self._delta())

    # --- borrados y vales sin fecha ------------------------------------------------------
    def test_una_pieza_borrada_no_cuenta(self):
        self._pieza("danado", borrada=True)
        self._renglon(self._pieza(borrada=True))
        self.assertEqual({}, self._delta())

    def test_un_renglon_o_un_vale_borrado_no_hacen_salida(self):
        self._renglon(self._pieza(), renglon_borrado=True)
        self._renglon(self._pieza(), vale_borrado=True)
        self.assertEqual({"Entrada": 2}, self._delta())

    def test_un_vale_sin_fecha_no_hace_salida(self):
        self._renglon(self._pieza(), sin_fecha=True)
        self.assertEqual({"Entrada": 1}, self._delta())

    # --- INVARIANTE ----------------------------------------------------------------------
    def test_la_suma_de_las_seis_categorias_es_el_total_de_piezas(self):
        pieza_doble = self._pieza()
        self._renglon(pieza_doble)
        self._renglon(pieza_doble)
        self._renglon(self._pieza("danado"))            # estado + prestamo
        self._renglon(self._pieza("extraviado"))
        self._renglon(self._pieza(), tipo=TIPO_DESTRUCCION)
        self._renglon(self._pieza(), close_date=CIERRE_SENTINELA)
        self._pieza("retirado")
        self._pieza("en_reparacion")
        self._pieza("danado", borrada=True)
        self._pieza()
        with transaction_context() as db:
            foto = _foto(db)
            total = _total_de_piezas(db)
        self.assertEqual(total, sum(foto.values()))
        self.assertEqual(self.base_total + 8, total)     # 9 piezas sembradas, 1 borrada
        self.assertEqual(sum(self.base.values()) + 8, sum(foto.values()))

    # --- muestra real del CSV de Alan ---------------------------------------------------
    def test_muestra_del_csv_de_alan(self):
        """Una fila real por cada tipo de "lectura" del CSV, sembrada y derivada.

        OJO: el CSV trae el estado ANTIGUO en texto (`estado_guardado`); aqui se traduce al catalogo con
        el mismo mapa de la migracion 20260929120000. La conciliacion contra `id_inventory_status`
        real de tyakxa-dev sigue pendiente.
        """
        catalogo = {"DESTRUCCION": "retirado", "DAÑADO": "danado", "EQ. DAÑADOS": "danado", "EXTRAVIADO": "extraviado"}
        with MUESTRA.open(encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f))
        self.assertGreaterEqual(len(filas), 10)
        esperado = {cat: 0 for cat in PIEZAS_CATEGORIAS}
        por_id = {}
        nombre = {"retirado": "Destruccion", "danado": "Dañado", "extraviado": "Extraviado"}
        for fila in filas:
            estado = catalogo.get(fila["estado_guardado"])
            pieza = self._pieza(estado)
            abiertos = int(fila["renglones_abiertos_en_prod_hoy"] or 0)
            # Fila 249: de sus 2 abiertos uno es un extravio (vale de baja) y otro un prestamo.
            for i in range(abiertos):
                self._renglon(pieza, tipo=TIPO_EXTRAVIADO if (fila["id_producto"] == "249" and i == 0) else TIPO_NORMAL)
            cat = nombre[estado] if estado else ("Salida" if abiertos else "Entrada")
            esperado[cat] += 1
            por_id[fila["id_producto"]] = cat
        self.assertEqual({c: n for c, n in esperado.items() if n}, self._delta())
        # Casos que se leen directo del CSV (columna `lectura`).
        self.assertEqual("Destruccion", por_id["228"])    # destruccion sin ningun vale
        self.assertEqual("Dañado", por_id["10"])          # EQ. DAÑADOS, sin vales
        self.assertEqual("Extraviado", por_id["12"])
        self.assertEqual("Salida", por_id["65"])          # ENTRADA guardado, prestamo abierto
        self.assertEqual("Entrada", por_id["72"])         # SALIDA guardado, todo devuelto
        self.assertEqual("Entrada", por_id["736"])

    # --- registro ------------------------------------------------------------------------
    def test_el_registro_lo_declara_como_foto_con_dona_y_colores_fijos(self):
        kpi = KPI_POR_CLAVE["piezas_por_estado"]
        self.assertEqual(("estado",), kpi.dimensiones)
        self.assertEqual("ultimo", kpi.agregacion)
        self.assertEqual("snapshot", kpi.modo)
        self.assertEqual("dona", kpi.grafica_default)
        self.assertEqual("neutral", kpi.direccion)
        self.assertEqual("Estado de la pieza", kpi.etiqueta_dimension)
        self.assertEqual(PIEZAS_CATEGORIAS, kpi.orden_categorias)
        self.assertEqual(set(PIEZAS_CATEGORIAS), set(PIEZAS_COLORES))
        self.assertEqual(PIEZAS_COLORES, kpi.colores_categoria)
        self.assertEqual("#8b6fe0", PIEZAS_COLORES["En reparación"])
        self.assertEqual(6, len(set(PIEZAS_COLORES.values())))

    def test_material_por_estado_no_cambio(self):
        kpi = KPI_POR_CLAVE["material_por_estado"]
        self.assertEqual({"Entrada", "Salida", "Dañado", "Extraviado", "Destruccion"}, set(kpi.colores_categoria))
        self.assertEqual("suma", kpi.agregacion)


if __name__ == "__main__":
    unittest.main()
