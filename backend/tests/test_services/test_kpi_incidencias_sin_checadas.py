"""Las checadas (filas de `incident` con coordenadas) no cuentan en los KPIs de incidencias.

Cada KPI se prueba con una incidencia normal y una checada, las dos del mismo usuario y del mismo dia: el KPI
debe contar solo la normal. Requiere PostgreSQL (`incidencias_pendientes` usa `generate_series`).
"""

from __future__ import annotations

import unittest
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.kpis.registry import (
    cancelaciones_por_empleado_query,
    incidencias_abiertas_por_empleado_query,
    incidencias_abiertas_vs_cerradas_query,
    incidencias_pendientes_query,
    incidentes_resueltos_por_empleado_query,
)
from app.models import Incident, IncidentType, User
from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_negocio

ADMIN_ID = 1
EMPLEADO = 980
TIPO = 980
LATITUD = Decimal("21.1161741")

AHORA = ahora_negocio().replace(hour=10, minute=0, second=0, microsecond=0)
HOY = AHORA.date()


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class KpiIncidenciasSinChecadasTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add(User(
                id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado checadas",
                id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                user_type="employee", is_employee=True, username="kpi-sin-checadas-test",
            ))
            db.add(IncidentType(id_incident_type=TIPO, incident_type_description="KPI sin checadas", created_by=ADMIN_ID))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Incident).where(Incident.id_incident_type == TIPO))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type == TIPO))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _incidente(self, id_incident, status, *, checada, cierre=None):
        return Incident(
            id_incident=id_incident, id_incident_type=TIPO, id_user=EMPLEADO, incident_status=status,
            incident_date=AHORA, close_date=cierre, created_by=EMPLEADO,
            latitude=LATITUD if checada else None,
        )

    def _sembrar(self, *incidentes):
        with transaction_context() as db:
            db.add_all(incidentes)

    def _filas(self, query):
        with transaction_context() as db:
            return [tuple(f) for f in query(db, HOY, HOY, {}, None)]

    def test_incidencias_pendientes_no_cuenta_la_checada_abierta(self):
        self._sembrar(self._incidente(9801, "abierta", checada=False), self._incidente(9802, "abierta", checada=True))
        con_normal_y_checada = self._filas(incidencias_pendientes_query)
        self._limpiar_incidentes()
        sin_nada = self._filas(incidencias_pendientes_query)
        # La base puede traer otras incidencias: lo que importa es que la checada no suma.
        self.assertEqual(sin_nada[0][2] + 1, con_normal_y_checada[0][2])

    def test_incidencias_abiertas_vs_cerradas_cuenta_solo_la_normal(self):
        cierre = AHORA + timedelta(hours=1)
        self._sembrar(
            self._incidente(9801, "cerrada", checada=False, cierre=cierre),
            self._incidente(9802, "cerrada", checada=True, cierre=cierre),
        )
        filas = {(estado, fecha): cantidad for estado, fecha, cantidad in self._filas(incidencias_abiertas_vs_cerradas_query)}
        self._limpiar_incidentes()
        base = {(estado, fecha): cantidad for estado, fecha, cantidad in self._filas(incidencias_abiertas_vs_cerradas_query)}
        for estado in ("abierta", "cerrada"):
            self.assertEqual(base.get((estado, HOY), 0) + 1, filas[(estado, HOY)], estado)

    def test_incidentes_resueltos_por_empleado_cuenta_solo_la_normal(self):
        self._sembrar(
            self._incidente(9801, "resuelta", checada=False),
            self._incidente(9802, "abierta", checada=False),
            self._incidente(9803, "resuelta", checada=True),
        )
        filas = [f for f in self._filas(incidentes_resueltos_por_empleado_query) if f[0] == EMPLEADO]
        # 1 resuelta de 2 incidencias normales = 50 %; con la checada habria sido 2 de 3 (66.67 %).
        self.assertEqual([(EMPLEADO, HOY, Decimal("50.00"), 2)], filas)

    def test_incidencias_abiertas_por_empleado_cuenta_solo_la_normal(self):
        self._sembrar(self._incidente(9801, "abierta", checada=False), self._incidente(9802, "abierta", checada=True))
        filas = [f for f in self._filas(incidencias_abiertas_por_empleado_query) if f[0] == EMPLEADO]
        self.assertEqual([(EMPLEADO, HOY, 1)], filas)

    def test_cancelaciones_por_empleado_cuenta_solo_la_normal(self):
        cierre = AHORA + timedelta(hours=1)
        self._sembrar(
            self._incidente(9801, "cancelada", checada=False, cierre=cierre),
            self._incidente(9802, "cancelada", checada=True, cierre=cierre),
        )
        filas = [f for f in self._filas(cancelaciones_por_empleado_query) if f[0] == EMPLEADO]
        self.assertEqual([(EMPLEADO, HOY, 1)], filas)

    def _limpiar_incidentes(self):
        with transaction_context() as db:
            db.execute(delete(Incident).where(Incident.id_incident_type == TIPO))


if __name__ == "__main__":
    unittest.main()
