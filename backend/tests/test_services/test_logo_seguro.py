"""El logo es texto libre que escribe quien da de alta al cliente y el motor de PDF lo
descarga: no debe poder apuntar a una URL (SSRF) ni a un archivo fuera de UPLOAD_ROOT."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from app import _doc_logo_uri, _documents_reports_app_path
from app.services.laboratory_report_service import LaboratoryReportService

PIXEL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="


class TestLogoSeguro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name).resolve()
        self.root = base / "uploads"
        self.root.mkdir()
        (self.root / "logo.png").write_bytes(b"png")
        (base / "secreto.png").write_bytes(b"secreto")  # fuera de UPLOAD_ROOT
        self.base = base
        patcher = mock.patch.dict(os.environ, {"UPLOAD_ROOT": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_a_file_inside_the_upload_root_is_accepted(self):
        esperado = "file://" + str(self.root / "logo.png")
        for valor in ("logo.png", "/logo.png", "uploads/logo.png", "/uploads/logo.png"):
            with self.subTest(valor):
                self.assertEqual(esperado, _doc_logo_uri(valor))

    def test_an_image_data_uri_is_accepted_but_not_other_types(self):
        self.assertEqual(PIXEL, _doc_logo_uri(PIXEL))
        self.assertEqual("", _doc_logo_uri("data:image/svg+xml;base64,PHN2Zy8+"))
        self.assertEqual("", _doc_logo_uri("data:text/html,<h1>x</h1>"))

    def test_urls_and_paths_outside_the_upload_root_are_dropped(self):
        for valor in ("http://169.254.169.254/latest/meta-data/", "https://interno:8080/x.png",
                      "file:///etc/passwd", "ftp://host/x.png", "../secreto.png",
                      "uploads/../secreto.png", "/etc/passwd", str(self.base / "secreto.png")):
            with self.subTest(valor):
                self.assertEqual("", _doc_logo_uri(valor))

    @unittest.skipUnless(hasattr(os, "symlink") and sys.platform != "win32", "sin enlaces simbolicos")
    def test_a_symlink_pointing_out_of_the_root_is_dropped(self):
        os.symlink(self.base / "secreto.png", self.root / "enlace.png")
        self.assertEqual("", _doc_logo_uri("enlace.png"))

    def test_the_laboratory_report_applies_the_same_rule(self):
        self.assertEqual((self.root / "logo.png").as_uri(), LaboratoryReportService._logo_uri("logo.png", self.root))
        for valor in ("../secreto.png", str(self.base / "secreto.png"), "/etc/passwd", "http://x/y.png"):
            with self.subTest(valor):
                self.assertEqual("", LaboratoryReportService._logo_uri(valor, self.root))


class TestPdfNoDescargaNada(unittest.TestCase):
    """El respaldo: aunque un valor malo llegue al HTML, el motor de PDF no lo pide."""

    def setUp(self):
        ruta = _documents_reports_app_path()
        if ruta not in sys.path:
            sys.path.insert(0, ruta)
        try:
            from documents.service import DocumentService  # noqa: F401
            import weasyprint  # noqa: F401
        except Exception as exc:  # falta el motor de PDF o el modulo de documentos
            self.skipTest("sin motor de PDF: %s" % exc)

    def test_the_pdf_engine_does_not_request_an_internal_url(self):
        from documents.service import DocumentService
        from weasyprint import HTML

        visitas = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                visitas.append(self.path)
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        servidor = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        plantillas = Path(tempfile.mkdtemp())
        html = '<img src="http://127.0.0.1:%d/ssrf.png"><img src="file:///etc/passwd">' % servidor.server_port

        from documents import service as modulo
        HTML(string=html, base_url=str(plantillas), url_fetcher=modulo._local_only_fetcher(plantillas)).write_pdf()

        self.assertEqual([], visitas)

    def test_the_fetcher_blocks_externals_and_allows_data_and_local_files(self):
        from documents import service as modulo

        plantillas = Path(tempfile.mkdtemp()).resolve()
        (plantillas / "a.png").write_bytes(b"x")
        for url in ("http://169.254.169.254/", "https://x/y.png", "file:///etc/passwd", "ftp://x/y"):
            with self.subTest(url):
                with self.assertRaises(ValueError):
                    modulo._check_local_only(url, plantillas)
        for url in (PIXEL, (plantillas / "a.png").as_uri(), (Path(os.environ["UPLOAD_ROOT"]) / "logo.png").as_uri()):
            with self.subTest(url[:30]):
                modulo._check_local_only(url, plantillas)  # no lanza

    def test_a_real_pdf_still_renders_its_local_and_data_images(self):
        from documents import service as modulo
        from weasyprint import HTML

        plantillas = Path(tempfile.mkdtemp()).resolve()
        html = '<img src="%s"><img src="%s">' % (PIXEL, (Path(os.environ["UPLOAD_ROOT"]) / "logo.png").as_uri())
        pdf = HTML(string=html, base_url=str(plantillas), url_fetcher=modulo._local_only_fetcher(plantillas)).write_pdf()
        self.assertTrue(pdf.startswith(b"%PDF"))
