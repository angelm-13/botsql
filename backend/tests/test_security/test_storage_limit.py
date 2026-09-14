"""El tope de almacenamiento del plan.

Lo que estas pruebas fijan, en orden de importancia:

* **pasarse del tope bloquea subidas, nunca operaciones.** Que no se pueda
  cobrar una venta o timbrar una factura porque el disco esta lleno seria peor
  que regalar el almacenamiento: se para el negocio del cliente por un problema
  nuestro de cobranza;
* **el XML de un comprobante ya timbrado se guarda igual.** Timbrar consume un
  folio ante el SAT y no se deshace; negarse a guardar su XML dejaria un
  comprobante existente sin respaldo, que es un problema fiscal. Un gigabyte de
  mas no lo es;
* se comprueba ANTES de escribir, no despues. Guardar y borrar deja el disco
  tocado y, si el proceso muere en medio, pasado de tope;
* sin tope en el plan no se estorba a nadie;
* se avisa antes de llegar, no al llegar: al cien por ciento la subida ya fallo.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.modules.plan import reiniciar_plan
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


def _con_tope(gigas):
    """Un plan con ese tope de almacenamiento."""
    return patch.dict(os.environ, {"TYAKXA_PLAN": '{"limites": {"almacenamiento_gb": %s}}' % gigas})


class TestElTopeDeAlmacenamiento(BackendTestCase):

    def setUp(self):
        super().setUp()
        reiniciar_plan()
        from app.services import storage_service
        storage_service._medicion = None

    def tearDown(self):
        reiniciar_plan()
        from app.services import storage_service
        storage_service._medicion = None
        super().tearDown()

    def test_without_a_limit_nothing_is_blocked(self):
        from app.services.storage_service import exigir_espacio, limite_bytes

        self.assertIsNone(limite_bytes())
        exigir_espacio(10 ** 12)  # un terabyte no molesta si no hay tope

    def test_it_refuses_an_upload_that_does_not_fit(self):
        from app.services import storage_service

        with _con_tope(1):
            with patch.object(storage_service, "uso_actual",
                              return_value={"bytes": 900 * 1024 ** 2, "files": 3, "folders": {}}):
                # Cabe: 900 MB usados + 50 MB entrantes contra 1 GB.
                storage_service.exigir_espacio(50 * 1024 ** 2)
                # No cabe: 900 + 200 pasa de 1024.
                with self.assertRaises(AppError) as capturado:
                    storage_service.exigir_espacio(200 * 1024 ** 2)
        self.assertEqual("errors.storage_limit_reached", capturado.exception.message_key)
        self.assertEqual(507, capturado.exception.status_code)

    def test_the_incoming_size_counts_before_writing(self):
        """Se comprueba antes de escribir, con el tamano que viene.

        Si solo se mirara lo ya usado, una subida de dos gigabytes entraria
        entera con el disco al noventa por ciento y lo dejaria pasado.
        """
        from app.services import storage_service

        with _con_tope(1):
            with patch.object(storage_service, "uso_actual",
                              return_value={"bytes": 1023 * 1024 ** 2, "files": 1, "folders": {}}):
                # Lo ya usado cabe, pero con lo que entra no.
                with self.assertRaises(AppError):
                    storage_service.exigir_espacio(5 * 1024 ** 2)

    def test_a_stamped_invoice_keeps_its_xml_even_over_the_limit(self):
        """La excepcion documentada.

        Un comprobante emitido sin XML es un problema fiscal; un gigabyte de mas
        no lo es.
        """
        from app.services import storage_service

        with _con_tope(0.000001):
            with patch.object(storage_service, "uso_actual",
                              return_value={"bytes": 10 ** 9, "files": 1, "folders": {}}):
                # El motivo documentado pasa aunque el tope este rebasado.
                storage_service.exigir_espacio(10 ** 6, motivo="comprobante_timbrado")
                # Cualquier otro motivo, y tambien no dar ninguno, se bloquea.
                # La exencion es de ese caso concreto, no una puerta que se abre
                # escribiendo cualquier texto en el motivo.
                with self.assertRaises(AppError):
                    storage_service.exigir_espacio(10 ** 6, motivo="adjunto_cualquiera")
                with self.assertRaises(AppError):
                    storage_service.exigir_espacio(10 ** 6)

    def test_it_warns_before_being_full_not_when_it_is(self):
        """Al cien por ciento la subida ya fallo y quien la intentaba se quedo a medias."""
        from app.services import storage_service

        with _con_tope(1):
            with patch.object(storage_service, "uso_actual",
                              return_value={"bytes": 900 * 1024 ** 2, "files": 1, "folders": {}}):
                estado = storage_service.estado()
        self.assertTrue(estado["nearly_full"])
        self.assertFalse(estado["over_limit"])
        self.assertGreater(estado["percent_used"], 85)

    def test_it_reports_what_is_left(self):
        from app.services import storage_service

        with _con_tope(2):
            with patch.object(storage_service, "uso_actual",
                              return_value={"bytes": 1024 ** 3, "files": 7, "folders": {}}):
                estado = storage_service.estado()
        self.assertEqual(1.0, estado["used_gb"])
        self.assertEqual(2.0, estado["limit_gb"])
        self.assertEqual(1024 ** 3, estado["available_bytes"])
        self.assertEqual(50.0, estado["percent_used"])

    def test_a_file_that_vanishes_while_measuring_does_not_break_it(self):
        """Un archivo borrado a media medicion no puede tirar la peticion.

        El total queda por debajo, que es el lado correcto en el que
        equivocarse: se cobra de menos, no se bloquea de mas.
        """
        from app.services import storage_service

        def falla(_ruta):
            raise OSError("desaparecio")

        with patch("os.walk", return_value=[("/uploads", [], ["fantasma.xml"])]), \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.getsize", side_effect=falla), \
             patch.object(storage_service, "_raiz", return_value="/uploads"):
            uso = storage_service.uso_actual(refrescar=True)
        self.assertEqual(0, uso["bytes"])
        self.assertEqual(0, uso["files"])


if __name__ == "__main__":
    unittest.main()
