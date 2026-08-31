"""Pruebas del endpoint de busqueda del catalogo c_ClaveProdServ.

Sin red y sin timbrado: solo la ruta HTTP contra la base de pruebas.
"""

from __future__ import annotations

import unittest

import jwt

from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.test_services.test_sat_catalog_service import seed_catalog


class TestSatCatalogApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        seed_catalog()
        token = jwt.encode(
            {"id_user": 1, "id_proyect": 1, "is_superuser": True},
            SECRET_KEY,
            algorithm="HS256",
        )
        self.headers = {"Authorization": f"Bearer {token}"}

    def _search(self, query, **params):
        query_string = {"q": query, **params}
        return self.client.get("/sat/clave-prod-serv", query_string=query_string, headers=self.headers)

    def test_text_search_returns_matching_keys(self):
        response = self._search("cemento")

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["catalog_loaded"])
        self.assertEqual("30111601", payload["items"][0]["clave"])

    def test_key_prefix_search(self):
        payload = self._search("432115").get_json()

        self.assertEqual(
            ["43211500", "43211503", "43211508"],
            [item["clave"] for item in payload["items"]],
        )

    def test_limit_is_forwarded(self):
        self.assertEqual(2, len(self._search("computador", limit=2).get_json()["items"]))

    def test_non_numeric_limit_does_not_break_the_request(self):
        response = self._search("computador", limit="abc")

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["items"])

    def test_empty_query_returns_no_items_but_still_reports_the_catalog(self):
        payload = self._search("").get_json()

        self.assertEqual([], payload["items"])
        self.assertTrue(payload["catalog_loaded"])

    def test_status_endpoint_reports_the_loaded_total(self):
        response = self.client.get("/sat/clave-prod-serv/status", headers=self.headers)

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["loaded"])
        self.assertGreater(payload["total"], 0)

    def test_both_routes_require_authentication(self):
        for path in ("/sat/clave-prod-serv?q=cemento", "/sat/clave-prod-serv/status"):
            with self.subTest(path=path):
                self.assertEqual(401, self.client.get(path).status_code)


class TestSatCatalogApiWithoutCatalog(BackendTestCase):
    """Si nadie importo el catalogo, la interfaz necesita poder avisarlo."""

    def setUp(self):
        super().setUp()
        token = jwt.encode(
            {"id_user": 1, "id_proyect": 1, "is_superuser": True},
            SECRET_KEY,
            algorithm="HS256",
        )
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_search_reports_the_catalog_is_not_loaded(self):
        payload = self.client.get(
            "/sat/clave-prod-serv", query_string={"q": "cemento"}, headers=self.headers
        ).get_json()

        self.assertEqual([], payload["items"])
        self.assertFalse(payload["catalog_loaded"])

    def test_status_reports_zero(self):
        payload = self.client.get("/sat/clave-prod-serv/status", headers=self.headers).get_json()

        self.assertEqual({"loaded": False, "total": 0}, payload)


if __name__ == "__main__":
    unittest.main()
