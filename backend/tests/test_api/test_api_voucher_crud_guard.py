"""`incident` y `nm_incident_product` son el vale y sus renglones: quien no es
administrador solo los mueve por `/vouchers`, no por el CRUD generico (que se salta
el libro de inventario y el registro de eventos del vale)."""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ESCRITURAS = (
    ("post", "/incident/"),
    ("put", "/incident/1"),
    ("post", "/incident/1/transition"),
    ("delete", "/incident/1"),
    ("post", "/nm_incident_product/"),
    ("put", "/nm_incident_product/1"),
    ("delete", "/nm_incident_product/1"),
)


class TestVoucherCrudGuard(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # Un Supervisor/Jefe de taller: CAPTURA completa sobre las dos entidades.
            db.add_all([EntityPermission(id_permission=401, entity_name=e, scope_create=4, scope_read=4,
                                         scope_update=4, scope_delete=4, created_by=1)
                        for e in ("incident", "nm_incident_product")])

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def test_a_non_admin_cannot_write_vouchers_through_the_generic_crud(self):
        headers = self._headers(id_user=41, id_permission=401)
        for metodo, ruta in ESCRITURAS:
            with self.subTest(ruta=ruta, metodo=metodo):
                respuesta = getattr(self.client, metodo)(ruta, json={"id_incident": 1}, headers=headers)
                self.assertEqual(403, respuesta.status_code)
                self.assertEqual("errors.voucher_use_voucher_flow", self.json(respuesta)["error_key"])

    def test_reading_stays_open_to_who_has_the_permission(self):
        headers = self._headers(id_user=41, id_permission=401)
        self.assertEqual(200, self.client.get("/incident/", headers=headers).status_code)
        self.assertEqual(200, self.client.get("/nm_incident_product/", headers=headers).status_code)

    def test_the_administrator_still_gets_past_the_guard(self):
        headers = self._headers(id_user=1, is_superuser=True)
        for metodo, ruta in ESCRITURAS:
            with self.subTest(ruta=ruta, metodo=metodo):
                respuesta = getattr(self.client, metodo)(ruta, json={"id_incident": 1}, headers=headers)
                self.assertNotEqual("errors.voucher_use_voucher_flow", self.json(respuesta).get("error_key"))
