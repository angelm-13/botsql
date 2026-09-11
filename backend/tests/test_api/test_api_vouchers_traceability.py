"""Las tres consultas de trazabilidad del vale, alcanzables desde el front.

Los servicios existian desde la carga del sistema anterior; las rutas no. Sin
ruta el dato esta en la base y no hay forma de verlo, asi que estas pruebas son
sobre lo unico que faltaba: que respondan y que la direccion llegue a la
funcion correcta.

El caso que de verdad importa es `/vouchers/holders`: convive con
`/vouchers/<id_incident>`, asi que si el enrutador prefiriera la regla dinamica,
"holders" se leeria como un identificador de vale y la respuesta seria un 400 de
validacion en lugar de la lista de quien tiene que. Werkzeug prefiere la parte
estatica, pero eso hay que comprobarlo, no suponerlo.
"""
from __future__ import annotations

import jwt

from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestVoucherTraceabilityApi(BackendTestCase):
    def cabeceras(self):
        """Un token firmado de verdad.

        `BackendTestCase.auth_headers()` devuelve la cadena "test-token", que
        `token_required` rechaza con 401 -- y como las pruebas generadas
        aceptan 401 como valido, pasan sin ejecutar la ruta. Firmando con la
        misma clave que valida la aplicacion, la peticion llega al handler y la
        prueba dice algo.
        """
        token = jwt.encode(
            {"id_user": 1, "id_permission": 1, "is_superuser": True,
             "is_bootstrap_admin": True},
            SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def test_holders_is_not_read_as_a_voucher_id(self):
        respuesta = self.client.get("/vouchers/holders", headers=self.cabeceras())
        self.assertEqual(200, respuesta.status_code)
        datos = self.json(respuesta)
        # La forma de `quien_tiene_que`, no la de `consultar_vale`: si la regla
        # dinamica hubiera ganado, "holders" seria un id de vale y esto seria un
        # 400 de validacion.
        self.assertIn("holders", datos)
        self.assertIn("total_holders", datos)
        self.assertNotIn("id_incident", datos)

    def test_requests_is_not_read_as_a_voucher_id(self):
        respuesta = self.client.get("/vouchers/requests", headers=self.cabeceras())
        self.assertEqual(200, respuesta.status_code)
        self.assertNotIn("id_incident", self.json(respuesta))

    def test_a_product_history_answers_with_its_own_shape(self):
        respuesta = self.client.get("/vouchers/products/1/history",
                                    headers=self.cabeceras())
        self.assertEqual(200, respuesta.status_code)
        datos = self.json(respuesta)
        for clave in ("id_product", "items", "currently_out",
                      "times_taken", "distinct_holders"):
            self.assertIn(clave, datos)

    def test_a_garbage_product_is_rejected_and_not_ignored(self):
        """Un identificador que no es numero es un error, no una lista vacia."""
        respuesta = self.client.get("/vouchers/products/abc/history",
                                    headers=self.cabeceras())
        self.assertEqual(400, respuesta.status_code)
