"""`GET /kpi_snapshot/query` de `perdidas_por_familia`: el top 10 al sumar el rango y los nombres.

Solo PostgreSQL (filtra `dimension_key` con JSONB). Va en su propio archivo: mezclar una
`BackendTestCase` con una `unittest.TestCase` rompe el clasificador de run_postgres_tests.sh.
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, KpiDefinition, KpiSnapshot, Level, Permission, ProductFamily,
    Proyect, Status, Subdepartment, User,
)
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase

ADMIN = {"id_user": 1, "is_superuser": True}
D1, D2 = date(2026, 9, 1), date(2026, 9, 2)
SEMANA_A = ("2026-09-01", "2026-09-02")


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestApiPerdidasPorFamilia(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # Mismo ciclo user <-> customer_supplier <-> proyect que test_api_kpi.py.
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            db.add(Permission(id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
                              id_department=1, id_subdepartment=1, id_level=1))
            db.add(User(id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=1, id_status=1,
                        supervisor=1, user_type="admin", username="kpi-perdidas-familia-api"))
            db.add(CustomerSupplier(id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                                    fiscal_type="601", type="supplier", id_user=1, created_by=1))
            db.add(Proyect(id_proyect=1, id_customer_supplier=1, leader=1, proyect_description="P", created_by=1))
            for id_familia in range(1, 13):
                db.add(ProductFamily(id_product_family=id_familia, product_family_description=f"Familia {id_familia}", created_by=1))
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.id_kpi = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "perdidas_por_familia"))
            # 12 familias con 1..12 piezas el dia 1; la familia 1 suma otras 100 el dia 2; "Sin familia" (0) con 3.
            for id_familia in range(1, 13):
                db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_familia": id_familia},
                                   periodo=D1, valor=Decimal(id_familia)))
            db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_familia": 1}, periodo=D2, valor=Decimal(100)))
            db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_familia": 0}, periodo=D2, valor=Decimal(3)))

    def _consultar(self, **params):
        params.setdefault("fecha_inicio", SEMANA_A[0])
        params.setdefault("fecha_fin", SEMANA_A[1])
        params["id_kpi_definition"] = self.id_kpi
        with patch("app.utils.auth.jwt.decode", return_value=ADMIN):
            respuesta = self.client.get("/kpi_snapshot/query?" + "&".join(f"{k}={v}" for k, v in params.items()),
                                        headers={"Authorization": "Bearer kpi-perdidas-familia"})
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return self.json(respuesta)

    def test_trae_las_10_familias_con_mas_perdidas_con_su_nombre_y_el_total_de_todas(self):
        rango = self._consultar()["rango_a"]
        # 1 (101), 12, 11, ..., 5, 4... y "Sin familia" (0) con 3 se queda fuera del top 10.
        self.assertEqual(["1", "12", "11", "10", "9", "8", "7", "6", "5", "4"],
                         sorted(rango["por_empleado"], key=lambda k: -rango["por_empleado"][k]))
        self.assertEqual(101.0, rango["por_empleado"]["1"])
        self.assertEqual(10, len(rango["por_empleado"]))
        # Los nombres viajan aparte: el snapshot solo guarda el id.
        self.assertEqual("Familia 1", rango["etiquetas"]["1"])
        self.assertEqual("Familia 12", rango["etiquetas"]["12"])
        # El total es el de TODAS (78 + 100 + 3), no el de las 10 que se muestran.
        self.assertEqual(181.0, rango["total"])

    def test_sin_familia_se_etiqueta_y_entra_al_top_si_le_toca(self):
        # Solo el dia 2: familia 1 (100) y "Sin familia" (3): ambas entran.
        rango = self._consultar(fecha_inicio="2026-09-02")["rango_a"]
        self.assertEqual({"1": 100.0, "0": 3.0}, rango["por_empleado"])
        self.assertEqual("Sin familia", rango["etiquetas"]["0"])

    def test_el_rango_de_comparacion_tambien_se_corta_y_trae_etiquetas(self):
        resultado = self._consultar(fecha_inicio_b="2026-09-01", fecha_fin_b="2026-09-01")
        rango_b = resultado["rango_b"]
        self.assertEqual(10, len(rango_b["por_empleado"]))
        self.assertEqual({"12", "11", "10", "9", "8", "7", "6", "5", "4", "3"}, set(rango_b["por_empleado"]))
        self.assertEqual("Familia 3", rango_b["etiquetas"]["3"])

    def test_agrupado_por_periodo_no_se_corta_ni_lleva_etiquetas(self):
        rango = self._consultar(agrupar_por="periodo")["rango_a"]
        self.assertEqual({"2026-09-01": 78.0, "2026-09-02": 103.0}, rango["por_periodo"])
        self.assertEqual(181.0, rango["total"])


if __name__ == "__main__":
    unittest.main()
