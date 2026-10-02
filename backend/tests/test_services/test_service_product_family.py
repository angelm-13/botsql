from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.product_family_service import ProductFamilyService


class TestProductFamilyService(BackendTestCase):
    def test_crud_service_product_family(self):
        created = ProductFamilyService.create(build_payload(ProductFamilyService, {'product_family_description': 'test description', 'type': 'tool', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = ProductFamilyService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)


class TestProductFamilyBusquedaYUnicidad(BackendTestCase):
    def _alta(self, descripcion, tipo='consumable'):
        return ProductFamilyService.create({'product_family_description': descripcion, 'type': tipo}, user_id=1)

    def _buscar(self, q, **kw):
        return ProductFamilyService.list(page=1, per_page=50, q=q, **kw)

    def test_la_busqueda_parcial_encuentra_la_familia(self):
        creada = self._alta('Refacciones')
        ids = [i['id_product_family'] for i in self._buscar('Ref')['items']]
        self.assertIn(creada['id_product_family'], ids)

    def test_la_busqueda_ignora_mayusculas(self):
        creada = self._alta('REFACCION')
        for q in ('refaccion', 'REFAC', 'ReFaCc'):
            ids = [i['id_product_family'] for i in self._buscar(q)['items']]
            self.assertIn(creada['id_product_family'], ids, q)

    def test_la_busqueda_ignora_acentos_en_ambos_sentidos(self):
        sin = self._alta('REFACCION')
        con = self._alta('Cañería Ácida')
        ids = [i['id_product_family'] for i in self._buscar('Refacción')['items']]
        self.assertIn(sin['id_product_family'], ids)
        for q in ('caneria', 'CAÑERÍA', 'acida'):
            ids = [i['id_product_family'] for i in self._buscar(q)['items']]
            self.assertIn(con['id_product_family'], ids, q)

    def test_el_total_coincide_con_las_filas_de_la_busqueda(self):
        self._alta('Refacciones')
        self._alta('Desarmadores')
        resultado = self._buscar('ref')
        self.assertEqual(resultado['total'], len(resultado['items']))
        self.assertTrue(all('ref' in i['product_family_description'].lower() for i in resultado['items']))

    def test_un_registro_recien_creado_sale_primero_sin_pedir_orden(self):
        self._alta('Primera')
        ultima = self._alta('Ultima')
        self.assertEqual(ProductFamilyService.list(page=1, per_page=5)['items'][0]['id_product_family'],
                         ultima['id_product_family'])

    def test_crear_un_duplicado_normalizado_da_409(self):
        from app.utils.errors import AppError
        self._alta('REFACCION')
        for repetido in ('Refacción', '  refaccion ', 'REFACCION'):
            with self.assertRaises(AppError) as ctx:
                self._alta(repetido)
            self.assertEqual(ctx.exception.status_code, 409)

    def test_la_variante_en_plural_no_cuenta_como_duplicado(self):
        self._alta('REFACCION')
        self.assertIsNotNone(self._alta('Refacciones'))

    def test_editar_una_familia_sin_cambiar_su_nombre_no_choca_consigo_misma(self):
        familia = self._alta('REFACCION')
        ProductFamilyService.update(familia['id_product_family'], {'product_family_description': 'REFACCION', 'type': 'tool'}, user_id=1)

    def test_editar_hacia_el_nombre_de_otra_familia_da_409(self):
        from app.utils.errors import AppError
        self._alta('REFACCION')
        otra = self._alta('Otra')
        with self.assertRaises(AppError) as ctx:
            ProductFamilyService.update(otra['id_product_family'], {'product_family_description': 'Refacción'}, user_id=1)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_una_familia_dada_de_baja_no_bloquea_el_nombre(self):
        from datetime import datetime
        familia = self._alta('REFACCION')
        ProductFamilyService.update(familia['id_product_family'], {'deletion_date': datetime(2026, 1, 1)}, user_id=1)
        self.assertIsNotNone(self._alta('Refacción'))
