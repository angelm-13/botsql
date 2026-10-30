import base64
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from app.services.stamping import FacturamaMultiemisorProvider, FacturamaSandboxProvider

XML = '<?xml version="1.0"?><cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"/>'


def _response(payload, status=201):
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(payload).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response
    return context


def _xml_payload():
    return {"Content": base64.urlsafe_b64encode(XML.encode("utf-8")).decode("ascii")}


class FacturamaDownloadXmlTest(unittest.TestCase):
    def _provider(self, cls=FacturamaSandboxProvider):
        return cls(base_url="https://apisandbox.facturama.mx", username="u", password="p")

    def test_stamp_downloads_the_xml_when_the_response_does_not_carry_it(self):
        provider = self._provider()
        with patch("app.services.stamping.urlopen") as urlopen:
            urlopen.side_effect = [
                _response({"Id": "abc123", "Complement": {"TaxStamp": {"Uuid": "UUID-1"}}}),
                _response(_xml_payload(), status=200),
            ]
            result = provider._post_cfdi({"x": 1}, "key-1")

        self.assertEqual("stamped", result.status)
        self.assertEqual("UUID-1", result.reference)
        self.assertEqual(XML, result.xml)
        self.assertEqual("abc123", result.metadata["facturama_id"])
        download_request = urlopen.call_args_list[1].args[0]
        self.assertTrue(download_request.full_url.endswith("/api/Cfdi/xml/issued/abc123"))

    def test_multiemisor_downloads_from_the_issued_lite_route(self):
        provider = self._provider(FacturamaMultiemisorProvider)
        with patch("app.services.stamping.urlopen") as urlopen:
            urlopen.return_value = _response(_xml_payload(), status=200)
            xml = provider.download_xml("abc123")

        self.assertEqual(XML, xml)
        self.assertTrue(urlopen.call_args.args[0].full_url.endswith("/api/Cfdi/xml/issuedLite/abc123"))

    def test_a_failed_download_does_not_undo_the_stamp(self):
        provider = self._provider()
        with patch("app.services.stamping.urlopen") as urlopen:
            urlopen.side_effect = [
                _response({"Id": "abc123", "Complement": {"TaxStamp": {"Uuid": "UUID-1"}}}),
                HTTPError("https://x", 500, "boom", {}, None),
            ]
            result = provider._post_cfdi({"x": 1}, "key-1")

        self.assertEqual("stamped", result.status)
        self.assertEqual("abc123", result.metadata["facturama_id"])
        self.assertIsNone(result.xml)


if __name__ == "__main__":
    unittest.main()
