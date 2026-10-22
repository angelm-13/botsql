"""Al pedir material, Compras se entera sin abrir la lista.

Quien compra es quien tiene `purchase_planning` y NO es de Gerencia ni de Almacen
(que tambien lo llevan, para ver "Por comprar"). El que pide no se avisa a si mismo.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models import EntityPermission, Notification, User
from app.models.session import transaction_context
from tests.model_factory import build_model
from tests.test_api.test_api_purchase_order import (
    ALMACEN, ALMACEN_1, BaseOrdenes, COMPRAS, COMPRAS_1, COMPRAS_2, GERENTE, GERENTE_1,
    PROYECTO_A, SUPERVISOR, _con_id,
)

LIDER_DE_A = 11  # PROYECTO_A lo lidera el usuario 11


class TestAvisoDeMaterialSolicitado(BaseOrdenes):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Gerencia y Almacen tambien ven "Por comprar", pero no compran.
                EntityPermission(id_permission=GERENTE, entity_name="purchase_planning",
                                 scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=ALMACEN, entity_name="purchase_planning",
                                 scope_read=4, created_by=1),
                EntityPermission(id_permission=ALMACEN, entity_name="purchase_receive",
                                 scope_read=4, scope_update=4, created_by=1),
            ])
            for id_user, permiso in ((COMPRAS_1, COMPRAS), (COMPRAS_2, COMPRAS),
                                     (GERENTE_1, GERENTE), (ALMACEN_1, ALMACEN)):
                db.add(_con_id(build_model(User, username="u%d" % id_user, email="u%d@x.mx" % id_user,
                                           id_permission=permiso, user_type="user"),
                               id_user=id_user))

    def _avisos(self, id_user):
        with transaction_context() as db:
            return [(n.notification_type, n.title, n.message, n.target_entity, n.target_id)
                    for n in db.scalars(select(Notification).where(
                        Notification.id_user_recipient == id_user)
                        .order_by(Notification.id_notification))]

    def _pedir(self, **datos):
        return self.client.post(
            "/proyect/%s/material-needs" % PROYECTO_A,
            json={"quantity": 4, "description": "Varilla de 3/8", **datos},
            headers=self._h(LIDER_DE_A, SUPERVISOR))

    def test_buyers_are_told_that_material_was_requested(self):
        self.assertEqual(201, self._pedir().status_code)

        for comprador in (COMPRAS_1, COMPRAS_2):
            avisos = self._avisos(comprador)
            self.assertEqual(1, len(avisos), comprador)
            tipo, titulo, mensaje, entidad, id_entidad = avisos[0]
            self.assertEqual("project_status_change", tipo)
            self.assertEqual("Material solicitado", titulo)
            self.assertIn("Varilla de 3/8", mensaje)
            self.assertEqual(("proyect", PROYECTO_A), (entidad, id_entidad))

    def test_management_and_the_warehouse_are_not_told(self):
        self.assertEqual(201, self._pedir().status_code)

        self.assertEqual([], self._avisos(GERENTE_1))
        self.assertEqual([], self._avisos(ALMACEN_1))

    def test_the_one_who_asks_is_not_told_about_his_own_request(self):
        self.assertEqual(201, self._pedir().status_code)

        self.assertEqual([], self._avisos(LIDER_DE_A))

    def test_a_rejected_request_tells_nobody(self):
        # Sin cantidad valida no se crea la necesidad: tampoco hay aviso.
        respuesta = self._pedir(quantity=0)
        self.assertEqual(400, respuesta.status_code)

        self.assertEqual([], self._avisos(COMPRAS_1))
