"""Cifras oficiales de nomina: validaciones de parametros y tarifa del ISR.

La pantalla "Cifras oficiales" solo captura; las reglas viven en los servicios
para que valgan igual por la API: claves conocidas, rangos y vigencias o tramos
que no se enciman (si se enciman, el calculo no sabria cual usar).
"""
from __future__ import annotations

import jwt

from app.models import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.fixtures.cifras_nomina_2026 import sembrar_cifras_2026


class TestCifrasOficiales(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            sembrar_cifras_2026(db)
            for entidad in ("payroll_parameter", "payroll_isr_bracket"):
                # 901 administra nomina; 902 solo consulta (como Gerente).
                db.add(EntityPermission(id_permission=901, entity_name=entidad, scope_create=4,
                                        scope_read=4, scope_update=4, scope_delete=4, created_by=1))
                db.add(EntityPermission(id_permission=902, entity_name=entidad, scope_create=0,
                                        scope_read=4, scope_update=0, scope_delete=0, created_by=1))

    def _admin(self):
        token = jwt.encode({"id_user": 1, "id_permission": 901, "user_type": "admin"}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def _solo_consulta(self):
        token = jwt.encode({"id_user": 41, "id_permission": 902}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def _parametro(self, **cambios):
        cuerpo = {"parameter_key": "uma_daily", "value": "121.00", "valid_from": "2027-02-01",
                  "valid_to": "2028-01-31", "source": "INEGI (prueba)"}
        cuerpo.update(cambios)
        return self.client.post("/payroll_parameter/", json=cuerpo, headers=self._admin())

    def _tramo(self, **cambios):
        cuerpo = {"period_days": 15, "valid_year": 2027, "lower_limit": "0.01", "upper_limit": "500.00",
                  "fixed_fee": "0", "rate_pct": "1.92"}
        cuerpo.update(cambios)
        return self.client.post("/payroll_isr_bracket/", json=cuerpo, headers=self._admin())

    # ---- parametros
    def test_un_valor_nuevo_con_otra_vigencia_se_guarda(self):
        self.assertEqual(201, self._parametro().status_code)

    def test_una_vigencia_que_se_encima_se_rechaza(self):
        # La UMA 2026 va del 1/02/2026 al 31/01/2027.
        respuesta = self._parametro(valid_from="2027-01-15")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.payroll_parameter_overlap", self.json(respuesta)["error_key"])

    def test_una_clave_que_el_calculo_no_conoce_se_rechaza(self):
        self.assertEqual(400, self._parametro(parameter_key="uma_semanal").status_code)

    def test_un_porcentaje_mayor_a_100_se_rechaza(self):
        self.assertEqual(400, self._parametro(parameter_key="imss_cv_pct", value="150",
                                              valid_from="2030-01-01", valid_to=None).status_code)

    def test_fin_antes_del_inicio_se_rechaza(self):
        self.assertEqual(400, self._parametro(valid_from="2027-02-01", valid_to="2027-01-01").status_code)

    def test_editar_un_valor_no_choca_consigo_mismo(self):
        nuevo = self.json(self._parametro())
        respuesta = self.client.put(f"/payroll_parameter/{nuevo['id_payroll_parameter']}",
                                    json={"value": "121.50"}, headers=self._admin())
        self.assertEqual(200, respuesta.status_code)

    def test_quien_solo_consulta_ve_pero_no_cambia(self):
        self.assertEqual(200, self.client.get("/payroll_parameter/", headers=self._solo_consulta()).status_code)
        respuesta = self.client.post("/payroll_parameter/", json={"parameter_key": "uma_daily", "value": "1",
                                                                  "valid_from": "2030-01-01"},
                                     headers=self._solo_consulta())
        self.assertEqual(403, respuesta.status_code)

    # ---- tarifa del ISR
    def test_un_tramo_de_otro_anio_se_guarda(self):
        self.assertEqual(201, self._tramo().status_code)

    def test_un_tramo_que_se_encima_se_rechaza(self):
        # La quincenal 2026 ya tiene 416.71 - 3,537.15.
        respuesta = self._tramo(valid_year=2026, lower_limit="1000.00", upper_limit="2000.00")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.payroll_isr_bracket_overlap", self.json(respuesta)["error_key"])

    def test_una_periodicidad_desconocida_se_rechaza(self):
        self.assertEqual(400, self._tramo(period_days=14).status_code)

    def test_limite_superior_menor_al_inferior_se_rechaza(self):
        self.assertEqual(400, self._tramo(lower_limit="500.00", upper_limit="100.00").status_code)

    def test_tasa_fuera_de_rango_se_rechaza(self):
        self.assertEqual(400, self._tramo(rate_pct="101").status_code)
