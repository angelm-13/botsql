"""Primeros pasos de RH (revision de usabilidad, 2026-11-05).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) con horario L-V, su jefe
Beto (80), Carla (81) y Rocio (82) de RH; el periodo 5 (1 al 15 de octubre).
"""
from __future__ import annotations

import jwt

from app.models import EntityPermission, PayrollGroup
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from app.services.primeros_pasos_rh import pasos
from app.utils.auth import SECRET_KEY
from tests.test_services.test_solicitudes_de_vacaciones import _ConEquipo


class TestPrimerosPasos(_ConEquipo):
    def paso(self, datos, clave):
        return next(p for p in datos["steps"] if p["key"] == clave)

    def test_marca_lo_listo_con_los_datos_reales(self):
        self.assertFalse(self.paso(pasos(), "groups")["done"])        # sin grupo por omision
        with transaction_context() as db:
            db.add(PayrollGroup(group_name="Quincenal", pay_frequency="semimonthly", is_default=True, created_by=1))
        datos = pasos()
        self.assertTrue(self.paso(datos, "groups")["done"])
        self.assertEqual(9, datos["total"])
        self.assertTrue(self.paso(datos, "schedules")["done"])
        self.assertTrue(self.paso(datos, "employees")["done"])
        # Beto, Carla y Rocio no tienen horario: quedan como datos de nomina pendientes.
        faltan = self.paso(datos, "payroll_data")
        self.assertFalse(faltan["done"])
        self.assertIn("Beto", faltan["names"])
        self.assertNotIn("Ana", faltan["names"])
        self.assertFalse(self.paso(datos, "calculated")["done"])
        self.assertEqual(datos["done"], sum(1 for p in datos["steps"] if p["done"]))

    def test_solicitudes_pendientes_y_periodo_calculado(self):
        self.pedir()
        self.assertEqual((False, 1), (self.paso(pasos(), "leaves")["done"], self.paso(pasos(), "leaves")["count"]))
        calcular_periodo(5, 1)
        datos = pasos()
        self.assertEqual((True, False), (self.paso(datos, "calculated")["done"], self.paso(datos, "closed")["done"]))

    def test_lo_controla_el_gestor(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=963, entity_name="rh_setup", scope_create=0, scope_read=4,
                                    scope_update=0, scope_delete=0, created_by=1))
        h = lambda permiso: {"Authorization": f"Bearer {jwt.encode({'id_user': 1, 'id_permission': permiso}, SECRET_KEY, algorithm='HS256')}"}  # noqa: E731
        self.assertEqual(200, self.client.get("/rh_setup/", headers=h(963)).status_code)
        self.assertEqual(403, self.client.get("/rh_setup/", headers=h(964)).status_code)
