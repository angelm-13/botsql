"""El XML timbrado vive en la base; el archivo es solo copia.

Falla real que motivo esto: en torredigital-prod los XML estaban solo en
/uploads/cfdi_xml, sin volumen persistente; un reinicio del pod los borraba y el
PDF de la factura salia sin QR, sin sello del emisor y sin cadena original,
porque todo eso se lee del XML.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.models import InvoiceCfdiXml
from app.models.session import transaction_context
from app.services.cfdi_xml_store import load_cfdi_xml, save_cfdi_xml
from app.services.invoice_artifacts import invoice_xml_path
from app.services.invoice_service import InvoiceService
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload

UUID_FACTURA = "11111111-2222-3333-4444-555555555555"
SELLO = "A" * 100 + "ZYXWVUTS"

CFDI = f'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="100.00" Total="116.00" Moneda="MXN" TipoDeComprobante="I" Sello="{SELLO}" NoCertificado="30001000000400000001">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" />
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87" Descripcion="Producto" ValorUnitario="100.00" Importe="100.00" ObjetoImp="01" />
  </cfdi:Conceptos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="{UUID_FACTURA}" FechaTimbrado="2026-08-27T15:58:33" RfcProvCertif="SPR190613I52" SelloCFD="{SELLO}" NoCertificadoSAT="30001000000400000002" SelloSAT="SATSEAL" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestCfdiXmlStore(BackendTestCase):
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

    def _factura(self):
        return InvoiceService.create(build_payload(
            InvoiceService, {"folio_fiscal": UUID_FACTURA, "created_by": 1, "id_proyect": 1}
        ))["id_invoice"]

    def _guardar(self, id_invoice, contenido=CFDI):
        with transaction_context() as db:
            save_cfdi_xml(db, id_invoice, contenido, self._upload_dir)

    def _borrar_archivo(self, id_invoice):
        os.remove(invoice_xml_path(id_invoice, self._upload_dir))

    def test_saving_writes_the_database_and_the_file(self):
        id_invoice = self._factura()
        self._guardar(id_invoice)

        with transaction_context() as db:
            self.assertEqual(CFDI, db.get(InvoiceCfdiXml, id_invoice).xml)
        self.assertTrue(invoice_xml_path(id_invoice, self._upload_dir).is_file())

    def test_the_xml_survives_losing_the_file(self):
        id_invoice = self._factura()
        self._guardar(id_invoice)
        self._borrar_archivo(id_invoice)

        self.assertEqual(CFDI.encode(), load_cfdi_xml(id_invoice, self._upload_dir))

    def test_without_a_row_it_falls_back_to_the_file(self):
        """Una factura anterior a esta tabla, con su archivo todavia en disco."""
        id_invoice = self._factura()
        path = invoice_xml_path(id_invoice, self._upload_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(CFDI.encode())

        self.assertEqual(CFDI.encode(), load_cfdi_xml(id_invoice, self._upload_dir))

    def test_without_row_or_file_there_is_no_xml(self):
        self.assertIsNone(load_cfdi_xml(self._factura(), self._upload_dir))
        self.assertIsNone(load_cfdi_xml(None, self._upload_dir))
        self.assertIsNone(load_cfdi_xml("no-es-un-numero", self._upload_dir))

    def test_saving_again_replaces_the_row(self):
        id_invoice = self._factura()
        self._guardar(id_invoice)
        self._guardar(id_invoice, CFDI.replace("EMISOR", "OTRO"))

        self.assertIn("OTRO", load_cfdi_xml(id_invoice, self._upload_dir).decode())
        with transaction_context() as db:
            self.assertEqual(1, db.query(InvoiceCfdiXml).count())

    def test_a_failed_file_copy_does_not_lose_the_database_row(self):
        id_invoice = self._factura()
        with patch("app.services.cfdi_xml_store.save_invoice_xml", side_effect=OSError("disco lleno")):
            self._guardar(id_invoice)

        self.assertEqual(CFDI.encode(), load_cfdi_xml(id_invoice, self._upload_dir))

    def test_the_pdf_record_has_the_qr_even_if_the_file_was_lost(self):
        from app import _load_quotation_document_record

        id_invoice = self._factura()
        self._guardar(id_invoice)
        self._borrar_archivo(id_invoice)

        with self.app.app_context():
            record = _load_quotation_document_record(str(id_invoice))

        self.assertTrue(record["qr_data_uri"].startswith("data:image/png;base64,"))
        self.assertEqual(SELLO, record["sello_cfdi"])
        self.assertEqual("SPR190613I52", record["rfc_proveedor_certificacion"])
        self.assertIn(UUID_FACTURA.upper(), record["cadena_original"])

    def test_the_pdf_record_has_no_qr_when_there_is_no_xml_anywhere(self):
        from app import _load_quotation_document_record

        id_invoice = self._factura()
        with self.app.app_context():
            record = _load_quotation_document_record(str(id_invoice))

        self.assertNotIn("qr_data_uri", record)

    def test_attaching_an_xml_stores_it_in_the_database(self):
        id_invoice = self._factura()
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            response = self.client.post(
                f"/invoice/{id_invoice}/xml",
                data={"file": (BytesIO(CFDI.encode()), "factura.xml")},
                headers={"Authorization": "Bearer cfdi-store-test"},
                content_type="multipart/form-data")
        self.assertEqual(200, response.status_code)

        self._borrar_archivo(id_invoice)
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            descarga = self.client.get(
                f"/invoice/{id_invoice}/xml", headers={"Authorization": "Bearer cfdi-store-test"})
        self.assertEqual(200, descarga.status_code)
        self.assertEqual(CFDI.encode(), descarga.data)
