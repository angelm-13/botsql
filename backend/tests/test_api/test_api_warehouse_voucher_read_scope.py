"""Quien puede LEER vales sin poder crearlos ni autorizarlos.

Antes de esto, las 11 rutas de solo lectura de `/vouchers*` exigian la
capacidad operativa `warehouse_voucher` -- la misma que crea/autoriza --, asi
que un Supervisor (solo `warehouse_prevoucher`) recibia 403 en la puerta
antes de poder ver ni sus propios vales ya autorizados, y Gerente (ninguna
capacidad de vale) no podia "ver/buscar el estado de almacen" en absoluto,
aunque el pedido de negocio lo exigiera explicitamente. `require_warehouse_read`
(en `warehouse_voucher.py`) abre la lectura sin tocar `_ve_todo_el_almacen`,
que sigue exigiendo `warehouse_voucher` especificamente para decidir "ve todo
vs. ve lo suyo".
"""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestWarehouseVoucherReadScope(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Supervisor: solo puede PEDIR (prevale), no crear/autorizar vales.
                EntityPermission(id_permission=201, entity_name="warehouse_prevoucher",
                                  scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Gerente: solo lectura sobre warehouse_voucher, sembrado tal
                # cual lo hace la migracion 20260921120000 (scope_create/update
                # en 0, scope_read=4 -"Todos"-, no el bit viejo LEER=2).
                EntityPermission(id_permission=301, entity_name="warehouse_voucher",
                                  scope_read=4, created_by=1),
            ])

    def _token(self, **claims):
        return jwt.encode(claims, SECRET_KEY, algorithm="HS256")

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % self._token(**claims)}

    def test_supervisor_can_list_vouchers_scoped_to_themselves(self):
        respuesta = self.client.get(
            "/vouchers",
            headers=self._headers(id_user=11, id_permission=201),
        )
        self.assertEqual(200, respuesta.status_code)
        self.assertTrue(self.json(respuesta).get("scoped_to_actor"))

    def test_supervisor_still_cannot_create_a_voucher(self):
        respuesta = self.client.post(
            "/vouchers",
            json={"id_incident_type": 1, "id_user": 11, "lines": []},
            headers=self._headers(id_user=11, id_permission=201),
        )
        self.assertEqual(403, respuesta.status_code)

    def test_manager_sees_the_whole_warehouse(self):
        respuesta = self.client.get(
            "/vouchers",
            headers=self._headers(id_user=21, id_permission=301),
        )
        self.assertEqual(200, respuesta.status_code)
        self.assertFalse(self.json(respuesta).get("scoped_to_actor"))

    def test_manager_cannot_create_or_authorize(self):
        crear = self.client.post(
            "/vouchers",
            json={"id_incident_type": 1, "id_user": 21, "lines": []},
            headers=self._headers(id_user=21, id_permission=301),
        )
        self.assertEqual(403, crear.status_code)

        autorizar = self.client.post(
            "/vouchers/1/authorize",
            json={},
            headers=self._headers(id_user=21, id_permission=301),
        )
        self.assertEqual(403, autorizar.status_code)

    def test_an_actor_with_no_warehouse_capability_at_all_is_still_rejected(self):
        respuesta = self.client.get(
            "/vouchers",
            headers=self._headers(id_user=99, id_permission=999),
        )
        self.assertEqual(403, respuesta.status_code)


class TestOpeningAVoucherByNumberIsScoped(BackendTestCase):
    """Abrir un vale por su numero (o bajar su PDF) respeta el mismo alcance que la lista.

    Antes solo la LISTA filtraba por responsable: con el numero de un vale ajeno en
    el buscador, un Supervisor o un Jefe de taller (solo `warehouse_prevoucher`) lo
    abria completo. Se contesta 404, igual que un numero que no existe.
    """

    def setUp(self):
        super().setUp()
        from app.models import Incident

        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=201, entity_name="warehouse_prevoucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=401, entity_name="warehouse_voucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
            ])
            suyo = Incident(id_incident_type=1, id_user=11, created_by=1, external_folio="9001")
            ajeno = Incident(id_incident_type=1, id_user=12, created_by=1, external_folio="9002")
            db.add_all([suyo, ajeno])
            db.flush()
            self.id_suyo, self.id_ajeno = suyo.id_incident, ajeno.id_incident

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def _pide(self, ruta, **claims):
        return self.client.get(ruta, headers=self._headers(**claims))

    def test_a_requester_opens_his_own_voucher(self):
        r = self._pide(f"/vouchers/{self.id_suyo}", id_user=11, id_permission=201)
        self.assertEqual(200, r.status_code)

    def test_a_requester_cannot_open_somebody_elses_voucher_by_id(self):
        r = self._pide(f"/vouchers/{self.id_ajeno}", id_user=11, id_permission=201)
        self.assertEqual(404, r.status_code)

    def test_nor_by_folio(self):
        r = self._pide("/vouchers/9002", id_user=11, id_permission=201)
        self.assertEqual(404, r.status_code)

    def test_nor_its_pdf(self):
        r = self._pide(f"/vouchers/{self.id_ajeno}/pdf", id_user=11, id_permission=201)
        self.assertEqual(404, r.status_code)

    def test_an_existing_and_a_missing_number_look_the_same(self):
        existe = self._pide(f"/vouchers/{self.id_ajeno}", id_user=11, id_permission=201)
        no_existe = self._pide("/vouchers/987654", id_user=11, id_permission=201)
        self.assertEqual(no_existe.status_code, existe.status_code)

    def test_whoever_operates_the_warehouse_opens_any_voucher(self):
        r = self._pide(f"/vouchers/{self.id_ajeno}", id_user=31, id_permission=401)
        self.assertEqual(200, r.status_code)
