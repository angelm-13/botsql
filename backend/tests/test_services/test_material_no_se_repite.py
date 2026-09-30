from __future__ import annotations

from app.services.material_service import MaterialService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


def _material(**cambios):
    datos = {
        'material_description': 'Desarmador plano',
        'id_unit': 1, 'id_brand': 1, 'id_product_family': 1, 'id_material_type': None,
        'created_by': 1,
    }
    datos.update(cambios)
    return build_payload(MaterialService, datos)


class TestMaterialNoSeRepite(BackendTestCase):
    """Un material no se captura dos veces: lo que en adser dejo 199 filas de mas."""

    def _rechazado(self, hacer):
        with self.assertRaises(AppError) as contexto:
            hacer()
        self.assertEqual(contexto.exception.message_key, 'errors.material_already_exists')
        self.assertEqual(contexto.exception.status_code, 409)
        return contexto.exception

    def test_el_mismo_material_dos_veces_se_rechaza_y_dice_cual_ya_existe(self):
        primero = MaterialService.create(_material())
        error = self._rechazado(lambda: MaterialService.create(_material()))
        self.assertEqual(error.meta['id_material'], primero['id_material'])

    def test_mayusculas_y_espacios_no_hacen_otro_material(self):
        MaterialService.create(_material())
        self._rechazado(lambda: MaterialService.create(_material(material_description='  DESARMADOR PLANO ')))

    def test_otra_marca_familia_unidad_o_tipo_si_es_otro_material(self):
        MaterialService.create(_material())
        for cambio in ({'id_brand': 2}, {'id_product_family': 2}, {'id_unit': 2}, {'id_material_type': 3}):
            with self.subTest(cambio=cambio):
                self.assertIsNotNone(MaterialService.create(_material(**cambio)))

    def test_sin_tipo_y_con_tipo_son_distintos_pero_dos_sin_tipo_no(self):
        MaterialService.create(_material(id_material_type=3))
        MaterialService.create(_material(id_material_type=None))
        self._rechazado(lambda: MaterialService.create(_material(id_material_type=None)))

    def test_uno_dado_de_baja_no_estorba(self):
        viejo = MaterialService.create(_material())
        MaterialService.update(viejo['id_material'], {'deletion_date': '2026-09-01T10:00:00'})
        self.assertIsNotNone(MaterialService.create(_material()))

    def test_editar_para_chocar_con_otro_se_rechaza(self):
        MaterialService.create(_material(material_description='Martillo'))
        otro = MaterialService.create(_material(material_description='Mazo'))
        self._rechazado(lambda: MaterialService.update(otro['id_material'], {'material_description': 'martillo '}))

    def test_editar_otra_cosa_o_dejarlo_igual_no_choca_consigo_mismo(self):
        propio = MaterialService.create(_material())
        MaterialService.update(propio['id_material'], {'material_description': 'Desarmador plano'})
        actualizado = MaterialService.update(propio['id_material'], {'id_brand': 5})
        self.assertEqual(actualizado['id_brand'], 5)
