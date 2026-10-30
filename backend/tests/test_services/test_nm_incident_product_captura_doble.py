from __future__ import annotations

from app.services.nm_incident_product_service import NmIncidentProductService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


def _renglon(**cambios):
    datos = {
        'id_incident': 10, 'id_product': 20, 'quantity': 1, 'direction': 'salida',
        'note': None, 'start_date': '2026-06-24T00:00:00', 'due_date': None,
        'close_date': None, 'id_inventory_asset': None,
        'id_location_from': None, 'id_location_to': None, 'created_by': 1,
    }
    datos.update(cambios)
    payload = build_payload(NmIncidentProductService, datos)
    # `build_payload` rellena todo lo que no se le da: lo que la prueba dejo en
    # nulo a proposito se vuelve a poner nulo.
    for campo, valor in datos.items():
        if valor is None:
            payload[campo] = None
    return payload


class TestNmIncidentProductCapturaDoble(BackendTestCase):
    """El mismo renglon guardado dos veces: lo que en adser dejo 62 renglones de mas."""

    def test_el_mismo_renglon_dos_veces_se_rechaza(self):
        primero = NmIncidentProductService.create(_renglon())
        with self.assertRaises(AppError) as contexto:
            NmIncidentProductService.create(_renglon())
        self.assertEqual(contexto.exception.message_key, 'errors.nm_incident_product_duplicate')
        self.assertEqual(contexto.exception.status_code, 409)
        self.assertEqual(contexto.exception.meta['id_nm_incident_product'], primero['id_nm_incident_product'])

    def test_una_diferencia_real_lo_deja_pasar(self):
        NmIncidentProductService.create(_renglon())
        distintos = (
            {'quantity': 2},
            {'note': 'segunda salida'},
            {'start_date': '2026-07-01T00:00:00'},
            {'close_date': '2026-07-03T00:00:00'},
            {'id_product': 21},
            {'id_incident': 11},
            {'id_inventory_asset': 5},
        )
        for cambio in distintos:
            with self.subTest(cambio=cambio):
                self.assertIsNotNone(NmIncidentProductService.create(_renglon(**cambio)))

    def test_el_historial_de_la_misma_herramienta_en_el_mismo_vale_no_se_toca(self):
        """Sacar la misma herramienta otra vez, ya devuelta la primera, es historial real."""
        NmIncidentProductService.create(_renglon(close_date='2026-06-30T00:00:00'))
        self.assertIsNotNone(NmIncidentProductService.create(_renglon(start_date='2026-07-05T00:00:00')))

    def test_uno_dado_de_baja_no_estorba(self):
        viejo = NmIncidentProductService.create(_renglon())
        NmIncidentProductService.update(
            viejo['id_nm_incident_product'], {'deletion_date': '2026-09-22T21:21:53'})
        self.assertIsNotNone(NmIncidentProductService.create(_renglon()))
