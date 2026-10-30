"""Quien puede usar el buscador del almacen (`GET /inventory/trace`).

El prevale de un Supervisor se arma tecleando el nombre del material y eligiendo
de las sugerencias; esas sugerencias salen de este endpoint. Antes exigia solo
`product` (lectura), asi que al quitarle el modulo Productos al Supervisor --
que es lo correcto, no administra el almacen -- el buscador del prevale se
quedaba vacio (el 403 se atrapa en la pantalla y no avisa). Ahora basta con
poder pedir material: `warehouse_voucher` o `warehouse_prevoucher`.
"""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestInventoryTraceAccess(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Supervisor: solo prevale. SIN fila de `product`.
                EntityPermission(id_permission=201, entity_name="warehouse_prevoucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Almacenista: vale. SIN fila de `product` tampoco.
                EntityPermission(id_permission=202, entity_name="warehouse_voucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Quien administra Productos pero no levanta vales.
                EntityPermission(id_permission=203, entity_name="product",
                                 scope_read=4, created_by=1),
                # Un rol con otra cosa: ni producto ni vales.
                EntityPermission(id_permission=204, entity_name="task",
                                 scope_read=4, created_by=1),
            ])

    def _headers(self, **claims):
        token = jwt.encode(claims, SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def _buscar(self, id_permission):
        return self.client.get(
            "/inventory/trace?q=taladro&per_page=8",
            headers=self._headers(id_user=11, id_permission=id_permission),
        )

    def test_a_supervisor_with_only_prevoucher_can_search_the_warehouse(self):
        self.assertEqual(200, self._buscar(201).status_code)

    def test_a_voucher_operator_without_product_permission_can_search(self):
        self.assertEqual(200, self._buscar(202).status_code)

    def test_product_read_alone_still_works(self):
        self.assertEqual(200, self._buscar(203).status_code)

    def test_a_role_with_neither_product_nor_voucher_capability_is_rejected(self):
        respuesta = self._buscar(204)
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.permission_denied", self.json(respuesta).get("error_key"))
