from __future__ import annotations

import unittest

from app.services.cfdi_xml import parse_cfdi


VALID_CFDI = b'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" SubTotal="100.00" Total="116.00" Moneda="MXN" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" />
  <cfdi:Receptor Rfc="BBB010101BBB" Nombre="RECEPTOR" RegimenFiscalReceptor="601" />
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="11111111-2222-3333-4444-555555555555" /></cfdi:Complemento>
</cfdi:Comprobante>'''


class TestCfdiXmlParser(unittest.TestCase):
    def test_parses_supported_cfdi_with_decimal_tax(self):
        result = parse_cfdi(VALID_CFDI)

        self.assertEqual(result["version"], "4.0")
        self.assertEqual(result["uuid"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(result["tax"], "16.00")

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