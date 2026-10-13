"""Barra final de las rutas y direccion publica para URLs absolutas.

Caso real (comala-prod): `curl .../api/user` (sin barra) devolvia el HTML de la
pagina. El Ingress reescribe `/api/user` a `/user` antes de llegar al backend;
las colecciones estan definidas como `/user/`, asi que Flask contestaba un 308 a
`/user/` -- sin el `/api` --, y esa ruta la sirve el frontend. n8n, Postman o un
script recibian React en vez de JSON.
"""
from __future__ import annotations

import os
from unittest import mock

from app.utils.public_url import image_url, public_base_url
from tests.conftest import BackendTestCase

REDIRECCIONES = {301, 302, 307, 308}


class TestBarraFinal(BackendTestCase):
    def test_a_collection_answers_the_same_with_or_without_the_trailing_slash(self):
        for ruta in ("/user", "/user/", "/permission", "/permission/"):
            respuesta = self.client.get(ruta)
            self.assertEqual(401, respuesta.status_code, "GET %s" % ruta)
            self.assertEqual("errors.auth_required", self.json(respuesta).get("error_key"), "GET %s" % ruta)

    def test_a_route_defined_without_slash_also_accepts_it(self):
        # `/vouchers` esta definida sin barra: con ella ya no da 404.
        for ruta in ("/vouchers", "/vouchers/"):
            self.assertEqual(401, self.client.get(ruta).status_code, "GET %s" % ruta)

    def test_no_get_route_redirects_because_of_a_trailing_slash(self):
        """Barrido: ninguna ruta GET sin parametros rebota por la barra final."""
        rutas = sorted({
            regla.rule for regla in self.app.url_map.iter_rules()
            if "GET" in regla.methods and not regla.arguments
        })
        self.assertGreater(len(rutas), 50, "el barrido no encontro rutas: la prueba pasaria vacia")
        for ruta in rutas:
            alterna = ruta.rstrip("/") if ruta.endswith("/") else ruta + "/"
            for candidata in (ruta, alterna):
                if candidata in ("", "/"):
                    continue
                estado = self.client.get(candidata).status_code
                self.assertNotIn(estado, REDIRECCIONES, "GET %s redirige (%s)" % (candidata, estado))


class TestUrlPublica(BackendTestCase):
    def test_public_base_url_wins_over_the_request_host(self):
        with mock.patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://comala.torredigital.mx/"}):
            with self.app.test_request_context("/", base_url="http://backend:5001"):
                self.assertEqual("https://comala.torredigital.mx", public_base_url())
                self.assertEqual("https://comala.torredigital.mx/uploads/products/1.png",
                                 image_url("uploads/products/1.png"))

    def test_without_the_variable_it_falls_back_to_the_request_host(self):
        entorno = {k: v for k, v in os.environ.items() if k != "PUBLIC_BASE_URL"}
        with mock.patch.dict(os.environ, entorno, clear=True):
            with self.app.test_request_context("/", base_url="http://backend:5001"):
                self.assertEqual("http://backend:5001", public_base_url())
                self.assertEqual("http://backend:5001/uploads/p.png", image_url("/uploads/p.png"))

    def test_absolute_and_empty_paths_are_left_alone(self):
        with self.app.test_request_context("/", base_url="http://backend:5001"):
            self.assertEqual("https://cdn.example.com/a.png", image_url("https://cdn.example.com/a.png"))
            self.assertEqual("", image_url(""))
            self.assertEqual("", image_url(None))

    def test_both_catalogs_share_the_same_helper(self):
        from app.routes import public_catalog, sales_catalog

        self.assertIs(public_catalog._image_url, image_url)
        self.assertIs(sales_catalog._image_url, image_url)
