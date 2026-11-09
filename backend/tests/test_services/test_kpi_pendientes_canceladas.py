"""`incidencias_pendientes` no cuenta una incidencia o vale CANCELADO como pendiente.

Una cancelada con el cierre centinela de 1990 (el que heredo Adser) o sin fecha de cierre se leia como
"sin cerrar" y entraba a la foto. Una cancelada no esta pendiente de resolver. Requiere PostgreSQL
(`incidencias_pendientes` usa `generate_series`).
"""

from __future__ import annotations

import unittest
from datetime import timedelta

from sqlalchemy import delete

from app.kpis.registry import incidencias_pendientes_query
from app.models import Incident, IncidentType, User
from app.models.session import engine, transaction_context
from app.services.warehouse_voucher_service import CIERRE_SENTINELA
from app.utils.tiempo import ahora_negocio

ADMIN_ID = 1
EMPLEADO = 985
TIPO = 985
AHORA = ahora_negocio().replace(hour=10, minute=0, second=0, microsecond=0)
HOY = AHORA.date()
ABIERTA, CANCELADA_SENTINELA, CANCELADA_SIN_CIERRE, VALE_CANCELADO = 9851, 9852, 9853, 9854


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class IncidenciasPendientesCanceladasTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add(User(
                id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado canceladas",
                id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                user_type="employee", is_employee=True, username="kpi-pendientes-canceladas-test",
            ))
            db.add(IncidentType(id_incident_type=TIPO, incident_type_description="KPI canceladas", created_by=ADMIN_ID))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Incident).where(Incident.id_incident_type == TIPO))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type == TIPO))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _incidente(self, id_incident, status, cierre=None):
        return Incident(id_incident=id_incident, id_incident_type=TIPO, id_user=EMPLEADO, incident_status=status,
                        incident_date=AHORA, close_date=cierre, created_by=EMPLEADO)

    def _pendientes_hoy(self):
        with transaction_context() as db:
            return {fecha: valor for _entidad, fecha, valor in incidencias_pendientes_query(db, HOY, HOY, {}, None)}[HOY]

    def _borrar(self, *ids):
        with transaction_context() as db:
            db.execute(delete(Incident).where(Incident.id_incident.in_(ids)))

    def test_las_canceladas_no_cuentan_como_pendientes(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(ABIERTA, "abierta"),
                self._incidente(CANCELADA_SENTINELA, "cancelada", CIERRE_SENTINELA),
                self._incidente(CANCELADA_SIN_CIERRE, "cancelada"),
                self._incidente(VALE_CANCELADO, "cancelado"),
            ])
        con_todo = self._pendientes_hoy()
        self._borrar(CANCELADA_SENTINELA, CANCELADA_SIN_CIERRE, VALE_CANCELADO)
        solo_la_abierta = self._pendientes_hoy()
        self._borrar(ABIERTA)
        sin_nada = self._pendientes_hoy()
        # La base puede traer otras incidencias: lo que importa es lo que suma cada una.
        self.assertEqual(sin_nada + 1, solo_la_abierta, "la abierta si cuenta")
        self.assertEqual(solo_la_abierta, con_todo, "ninguna cancelada suma")

    def test_una_cancelada_con_cierre_real_sigue_pendiente_hasta_cancelarse(self):
        # Abierta hace 3 dias y cancelada hace 1: estuvo pendiente antes de cancelarse (historia), ya no despues.
        abierta_el = AHORA - timedelta(days=3)
        cancelada_el = AHORA - timedelta(days=1)
        antes, despues = HOY - timedelta(days=2), HOY

        def pendientes():
            with transaction_context() as db:
                return {f: v for _e, f, v in incidencias_pendientes_query(db, antes, despues, {}, None)}

        sin_nada = pendientes()
        with transaction_context() as db:
            db.add(Incident(id_incident=ABIERTA, id_incident_type=TIPO, id_user=EMPLEADO, incident_status="cancelada",
                            incident_date=abierta_el, close_date=cancelada_el, created_by=EMPLEADO))
        con_ella = pendientes()
        self.assertEqual(sin_nada[antes] + 1, con_ella[antes], "pendiente antes de cancelarse")
        self.assertEqual(sin_nada[HOY], con_ella[HOY], "ya no pendiente despues de cancelarse")
