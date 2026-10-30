from __future__ import annotations

import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.services.invoice_service import InvoiceService
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload

UUID_FACTURA = "11111111-2222-3333-4444-555555555555"

CFDI = f'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="100.00" Total="116.00" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" />
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87" Descripcion="Producto" ValorUnitario="100.00" Importe="100.00" ObjetoImp="01" />
  </cfdi:Conceptos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="{{uuid}}" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestAttachInvoiceXml(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.actor = {"id_user": 1, "is_superuser": True}
        self._upload_dir = tempfile.mkdtemp()
        self._env = patch.dict(os.environ, {"UPLOAD_ROOT": self._upload_dir})
        self._env.start()
        self.app.config["UPLOAD_ROOT"] = self._upload_dir

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self._upload_dir, ignore_errors=True)
        super().tearDown()

    def _factura(self, folio_fiscal=UUID_FACTURA):
        return InvoiceService.create(build_payload(
            InvoiceService, {"folio_fiscal": folio_fiscal, "created_by": 1, "id_proyect": 1}
        ))["id_invoice"]

    def _adjuntar(self, id_invoice, contenido):
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            return self.client.post(
                f"/invoice/{id_invoice}/xml",
                data={"file": (BytesIO(contenido), "factura.xml")},
                headers={"Authorization": "Bearer attach-xml-test"},
                content_type="multipart/form-data")

    def _descargar(self, id_invoice):
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            return self.client.get(
                f"/invoice/{id_invoice}/xml", headers={"Authorization": "Bearer attach-xml-test"})

    def test_attaching_the_matching_xml_makes_it_downloadable(self):
        id_invoice = self._factura()
        self.assertEqual(404, self._descargar(id_invoice).status_code)

        response = self._adjuntar(id_invoice, CFDI.format(uuid=UUID_FACTURA).encode())

        self.assertEqual(200, response.status_code)
        self.assertTrue(os.path.isfile(os.path.join(self._upload_dir, "cfdi_xml", f"invoice_{id_invoice}.xml")))
        self.assertEqual(200, self._descargar(id_invoice).status_code)

    def test_the_uuid_comparison_ignores_letter_case(self):
        id_invoice = self._factura()
        response = self._adjuntar(id_invoice, CFDI.format(uuid=UUID_FACTURA.lower()).encode())
        self.assertEqual(200, response.status_code)

    def test_an_xml_from_another_invoice_is_rejected_and_not_saved(self):
        id_invoice = self._factura()

        response = self._adjuntar(id_invoice, CFDI.format(uuid="99999999-2222-3333-4444-555555555555").encode())

        self.assertEqual(422, response.status_code)
        self.assertEqual("invoice.xml_uuid_mismatch", self.json(response)["error_key"])
        self.assertFalse(os.path.exists(os.path.join(self._upload_dir, "cfdi_xml", f"invoice_{id_invoice}.xml")))

    def test_a_file_that_is_not_a_cfdi_is_rejected(self):
        id_invoice = self._factura()
        response = self._adjuntar(id_invoice, b"hola, no soy un xml")
        self.assertEqual(422, response.status_code)
        self.assertEqual("invoice.xml_invalid", self.json(response)["error_key"])

    def test_a_missing_invoice_answers_404(self):
        response = self._adjuntar(999999, CFDI.format(uuid=UUID_FACTURA).encode())
        self.assertEqual(404, response.status_code)
