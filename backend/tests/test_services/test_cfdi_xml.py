from __future__ import annotations

import unittest

from app.services.cfdi_xml import parse_cfdi


VALID_CFDI = b'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="100.00" Descuento="5.00" Total="107.00" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" />
    <cfdi:Conceptos>
        <cfdi:Concepto ClaveProdServ="81111500" Cantidad="2" ClaveUnidad="E48" Descripcion="Servicio de software" ValorUnitario="40.00" Importe="80.00" Descuento="5.00" ObjetoImp="02">
            <cfdi:Impuestos><cfdi:Traslados><cfdi:Traslado Base="75.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="12.00" /></cfdi:Traslados></cfdi:Impuestos>
        </cfdi:Concepto>
        <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87" Descripcion="Producto de prueba" ValorUnitario="20.00" Importe="20.00" ObjetoImp="01" />
    </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="12.00"><cfdi:Traslados><cfdi:Traslado Base="75.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="12.00" /></cfdi:Traslados></cfdi:Impuestos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="11111111-2222-3333-4444-555555555555" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestCfdiXmlParser(unittest.TestCase):
    def test_parses_supported_cfdi_with_decimal_tax(self):
        result = parse_cfdi(VALID_CFDI)

        self.assertEqual(result["version"], "4.0")
        self.assertEqual(result["uuid"], "11111111-2222-3333-4444-555555555555")
        # El IVA se lee del comprobante, no como Total - SubTotal: con
        # descuento o retenciones esa resta daba un importe equivocado.
        self.assertEqual(result["tax"], "12.00")
        self.assertEqual(result["retained_tax"], "0.00")
        self.assertEqual(result["total"], "107.00")

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


RETENTION_CFDI = b'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="10000.00" Total="9533.33" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" RegimenFiscal="612" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" UsoCFDI="G03" />
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111500" Cantidad="1" ClaveUnidad="E48" Descripcion="Honorarios" ValorUnitario="10000.00" Importe="10000.00" ObjetoImp="02">
      <cfdi:Impuestos>
        <cfdi:Traslados><cfdi:Traslado Base="10000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="1600.00" /></cfdi:Traslados>
        <cfdi:Retenciones>
          <cfdi:Retencion Base="10000.00" Impuesto="001" TipoFactor="Tasa" TasaOCuota="0.100000" Importe="1000.00" />
          <cfdi:Retencion Base="10000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.106667" Importe="1066.67" />
        </cfdi:Retenciones>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosRetenidos="2066.67" TotalImpuestosTrasladados="1600.00">
    <cfdi:Retenciones><cfdi:Retencion Impuesto="001" Importe="1000.00" /><cfdi:Retencion Impuesto="002" Importe="1066.67" /></cfdi:Retenciones>
    <cfdi:Traslados><cfdi:Traslado Base="10000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="1600.00" /></cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="99999999-8888-7777-6666-555555555555" /></cfdi:Complemento>
</cfdi:Comprobante>'''

EXEMPT_CFDI = b'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="500.00" Total="500.00" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" RegimenFiscal="601" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" UsoCFDI="G01" />
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="50192700" Cantidad="1" ClaveUnidad="H87" Descripcion="Alimento exento" ValorUnitario="500.00" Importe="500.00" ObjetoImp="02">
      <cfdi:Impuestos><cfdi:Traslados><cfdi:Traslado Base="500.00" Impuesto="002" TipoFactor="Exento" /></cfdi:Traslados></cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="12121212-3434-5656-7878-909090909090" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestCfdiTaxExtraction(unittest.TestCase):
    def test_retentions_are_read_from_the_summary_node(self):
        """Total - SubTotal daba un IVA negativo en facturas con retenciones."""
        result = parse_cfdi(RETENTION_CFDI)

        self.assertEqual(result["tax"], "1600.00")
        self.assertEqual(result["retained_tax"], "2066.67")
        self.assertEqual(result["total"], "9533.33")

    def test_taxes_fall_back_to_the_concept_breakdown(self):
        """Un CFDI sin nodo resumen se resuelve sumando los conceptos."""
        import re

        without_summary = re.sub(
            rb'<cfdi:Impuestos TotalImpuestos.*?</cfdi:Impuestos>',
            b'',
            RETENTION_CFDI,
            flags=re.DOTALL,
        )
        result = parse_cfdi(without_summary)

        self.assertEqual(result["tax"], "1600.00")
        self.assertEqual(result["retained_tax"], "2066.67")

    def test_exempt_concept_is_flagged_and_not_read_as_zero_rate(self):
        concept = parse_cfdi(EXEMPT_CFDI)["conceptos"][0]

        self.assertTrue(concept["iva_exempt"])
        self.assertIsNone(concept["tax_rate"])
        self.assertEqual(concept["tax"], "0")

    def test_non_exempt_concept_is_not_flagged(self):
        concept = parse_cfdi(RETENTION_CFDI)["conceptos"][0]

        self.assertFalse(concept["iva_exempt"])
        self.assertEqual(concept["tax_rate"], "0.160000")


if __name__ == "__main__":
    unittest.main()
