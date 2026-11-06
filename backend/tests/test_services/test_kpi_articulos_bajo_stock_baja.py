"""`articulos_bajo_stock` no cuenta un producto dado de baja aunque conserve saldo.

Un producto con `deletion_date` ya no existe para el negocio: su existencia no es un "articulo bajo stock"
que alguien deba reponer. Requiere PostgreSQL, como el resto de las pruebas de KPI.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime

from sqlalchemy import delete

from app.kpis.registry import articulos_bajo_stock_query
from app.models import (
    Brand, InventoryStock, Invoice, Location, LocationType, Material, Product, ProductFamily, Unit,
)
from app.models.session import engine, transaction_context

ADMIN_ID = 1
LOCATION_TYPE = 990
LOCATION = 990
BRAND = 990
PRODUCT_FAMILY = 990
UNIT = 990
MATERIAL = 990
INVOICE = 990
PRODUCTO_VIGENTE = 990
PRODUCTO_DE_BAJA = 991
HOY = date(2031, 10, 1)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class ArticulosBajoStockBajaTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add(LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI baja", is_warehouse=True, created_by=ADMIN_ID))
            db.add(Brand(id_brand=BRAND, brand_description="KPI baja", created_by=ADMIN_ID))
            db.add(ProductFamily(id_product_family=PRODUCT_FAMILY, product_family_description="KPI baja", created_by=ADMIN_ID))
            db.add(Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID))
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI baja", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI baja", id_unit=UNIT, id_brand=BRAND,
                            id_product_family=PRODUCT_FAMILY, created_by=ADMIN_ID))
            db.add(Invoice(
                id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1, id_proyect=1, id_status=1,
                tax_certification_supplier=1, apply_tax=False, invoice_status="pendiente", created_by=ADMIN_ID,
            ))
            db.flush()
            for id_product, baja in ((PRODUCTO_VIGENTE, None), (PRODUCTO_DE_BAJA, datetime(2031, 9, 1))):
                db.add(Product(
                    id_product=id_product, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                    is_directly_related_to_product_service=False, cantidad=7, created_by=ADMIN_ID, deletion_date=baja,
                ))
            db.flush()
            for id_product in (PRODUCTO_VIGENTE, PRODUCTO_DE_BAJA):
                db.add(InventoryStock(id_product=id_product, id_location=LOCATION, quantity=7, created_by=ADMIN_ID))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        productos = [PRODUCTO_VIGENTE, PRODUCTO_DE_BAJA]
        with transaction_context() as db:
            db.execute(delete(InventoryStock).where(InventoryStock.id_product.in_(productos)))
            db.execute(delete(Product).where(Product.id_product.in_(productos)))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))

    def _filas(self, **filtros):
        with transaction_context() as db:
            return {id_product: cantidad for id_product, _fecha, cantidad in articulos_bajo_stock_query(db, HOY, HOY, filtros, None)}

    def test_un_producto_dado_de_baja_con_saldo_no_aparece(self):
        filas = self._filas()
        self.assertEqual(7, filas.get(PRODUCTO_VIGENTE))
        self.assertNotIn(PRODUCTO_DE_BAJA, filas)

    def test_el_filtro_por_producto_tampoco_lo_trae(self):
        filas = self._filas(productos=[PRODUCTO_VIGENTE, PRODUCTO_DE_BAJA])
        self.assertEqual({PRODUCTO_VIGENTE: 7}, filas)
