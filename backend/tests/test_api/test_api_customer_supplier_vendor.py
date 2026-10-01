from __future__ import annotations

from unittest.mock import patch

from tests.conftest import BackendTestCase


class TestCustomerSupplierVendorDefault(BackendTestCase):
    """El vendedor (`id_user`) es NOT NULL pero ya no se captura en el formulario."""

    def test_creating_without_a_vendor_assigns_the_actor(self):
        id_actor = 1
        actor = {"id_user": id_actor, "is_superuser": True}
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            respuesta = self.client.post(
                "/customer_supplier/", json={"name": "Cliente sin vendedor", "type": "client"},
                headers={"Authorization": "Bearer vendedor-por-omision"})

        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        self.assertEqual(id_actor, self.json(respuesta)["id_user"])
