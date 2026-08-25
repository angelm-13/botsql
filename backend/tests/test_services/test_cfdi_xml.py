from __future__ import annotations

import unittest

from app.services.cfdi_xml import parse_cfdi


VALID_CFDI = b'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="100.00" Total="116.00" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" />
    <cfdi:Conceptos>
        <cfdi:Concepto ClaveProdServ="81111500" Cantidad="2" ClaveUnidad="E48" Descripcion="Servicio de software" ValorUnitario="40.00" Importe="80.00" Descuento="5.00" ObjetoImp="02">
            <cfdi:Impuestos><cfdi:Traslados><cfdi:Traslado Base="75.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="12.00" /></cfdi:Traslados></cfdi:Impuestos>
        </cfdi:Concepto>
        <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87" Descripcion="Producto de prueba" ValorUnitario="20.00" Importe="20.00" ObjetoImp="01" />
    </cfdi:Conceptos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="11111111-2222-3333-4444-555555555555" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestCfdiXmlParser(unittest.TestCase):
    def test_parses_supported_cfdi_with_decimal_tax(self):
        result = parse_cfdi(VALID_CFDI)

        self.assertEqual(result["version"], "4.0")
        self.assertEqual(result["uuid"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(result["tax"], "16.00")

    def test_parses_invoice_concepts_and_taxes(self):
        concepts = parse_cfdi(VALID_CFDI)["conceptos"]

        self.assertEqual(2, len(concepts))
        self.assertEqual("Servicio de software", concepts[0]["description"])
        self.assertEqual("81111500", concepts[0]["sat_product_key"])
        self.assertEqual("E48", concepts[0]["sat_unit_key"])
        self.assertEqual("2", concepts[0]["quantity"])
        self.assertEqual("40.00", concepts[0]["unit_price"])
        self.assertEqual("5.00", concepts[0]["discount"])
        self.assertEqual("12.00", concepts[0]["tax"])
        self.assertEqual("87.00", concepts[0]["total"])
        self.assertEqual("01", concepts[1]["tax_object"])

    def test_rejects_dtd_and_entities(self):
        malicious = b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><Comprobante Version="4.0">&secret;</Comprobante>'

        with self.assertRaisesRegex(ValueError, "DTD"):
            parse_cfdi(malicious)

    def test_rejects_oversized_xml(self):
        with self.assertRaisesRegex(ValueError, "excede"):
            parse_cfdi(VALID_CFDI, max_bytes=10)

    def test_rejects_non_cfdi_and_missing_uuid(self):
        with self.assertRaisesRegex(ValueError, "no es un comprobante"):
            parse_cfdi(b'<root Version="4.0" />')

        with self.assertRaisesRegex(ValueError, "UUID"):
            parse_cfdi(b'<Comprobante Version="4.0" SubTotal="1" Total="1" />')


if __name__ == "__main__":
    unittest.main()