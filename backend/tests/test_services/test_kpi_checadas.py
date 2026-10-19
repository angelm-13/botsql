"""KPIs de checadas (entrada/salida) de Comala: filas de `incident` con coordenadas.

Corren en SQLite y en PostgreSQL (solo usan SQL portable). `incident_date` y `close_date` son hora de pared
del negocio, sin zona; "ahora" sale de `ahora_negocio()`, que aqui se congela en un instante UTC concreto y
deja que el codigo real haga la conversion a hora de Mexico (UTC-6 todo el ano desde 2022).
"""

from __future__ import annotations

import copy
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

from sqlalchemy import select, text

from app.jobs import tasks_kpis
from app.kpis import frecuencia
from app.kpis.modulos import checadas
from app.kpis.modulos.checadas import (
    UMBRAL_SIN_SALIDA_HORAS,
    checadas_en_turno_por_equipo_query,
    checadas_entradas_por_equipo_query,
    checadas_salidas_por_equipo_query,
    checadas_sin_salida_por_equipo_query,
    horas_trabajadas_por_empleado_query,
)
from app.kpis.registry import KPI_POR_CLAVE, seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, Incident, IncidentType, KpiDefinition, KpiSnapshot, Level, NmTeamUser, Permission,
    Proyect, Status, Subdepartment, Team, User,
)
from app.models.session import engine, transaction_context
from app.services.incident_service import IncidentService
from tests.conftest import BackendTestCase
from tests.reloj import ahora_local, reloj_en_utc

# Personas
ANA, BETO, CARLA, DIEGO, ELENA = 101, 102, 103, 104, 105
# Equipos (parques)
NORTE, SUR, VACIO, BAJA = 7001, 7002, 7003, 7004
PROYECTO_OTRO = 2
LATITUD = Decimal("21.1161741")

# Un dia de referencia (jueves 15 de octubre de 2026) y su siguiente.
D = date(2026, 10, 15)
D1 = date(2026, 10, 16)


def local(dia: date, hora: int, minuto: int = 0, segundo: int = 0) -> datetime:
    """Una hora de pared del negocio, sin zona: como se guarda `incident_date`."""
    return datetime(dia.year, dia.month, dia.day, hora, minuto, segundo)


class ChecadasBase(BackendTestCase):
    """Personas, equipos y una checada por helper. Ids propios; cada prueba arranca de un esquema vacio."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            if engine.dialect.name == "postgresql":
                db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            db.add(Permission(
                id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
                id_department=1, id_subdepartment=1, id_level=1,
            ))
            db.add(User(
                id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=1,
                id_status=1, supervisor=1, user_type="admin", username="checadas-admin",
            ))
            for id_user, nombre in ((ANA, "Ana"), (BETO, "Beto"), (CARLA, "Carla"), (DIEGO, "Diego"), (ELENA, "Elena")):
                db.add(User(
                    id_user=id_user, created_by=1, full_name=nombre, id_permission=1, id_proyect=1,
                    id_status=1, supervisor=1, user_type="employee", username=f"checadas-{id_user}",
                ))
            db.add(CustomerSupplier(
                id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                fiscal_type="601", type="supplier", id_user=1, created_by=1,
            ))
            for id_proyect in (1, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=id_proyect, id_customer_supplier=1, leader=1,
                    proyect_description=f"Proyecto {id_proyect}", created_by=1,
                ))
            db.add(IncidentType(id_incident_type=1, incident_type_description="Checador", created_by=1))
            db.flush()
            for id_team, nombre, baja in (
                (NORTE, "Parque Norte", None), (SUR, "Parque Sur", None), (VACIO, "Parque Vacio", None),
                (BAJA, "Parque Cerrado", datetime(2026, 1, 1)),
            ):
                db.add(Team(id_team=id_team, team_description=nombre, created_by=1, deletion_date=baja))
            db.flush()
            # Beto esta en DOS equipos; Diego en ninguno; la membresia de Elena en Norte esta dada de baja;
            # Ana tambien esta en un equipo que ya no existe (no debe aparecer).
            for id_team, id_user, baja in (
                (NORTE, ANA, None), (NORTE, BETO, None), (SUR, BETO, None), (SUR, CARLA, None),
                (NORTE, ELENA, datetime(2026, 6, 1)), (BAJA, ANA, None),
            ):
                db.add(NmTeamUser(id_team=id_team, id_user=id_user, created_by=1, deletion_date=baja))
        self._siguiente_id = 0

    def _checada(self, id_user, abre, cierra=None, *, latitude=LATITUD, status=None, id_proyect=None, baja=None):
        self._siguiente_id += 1
        with transaction_context() as db:
            db.add(Incident(
                id_incident=self._siguiente_id, id_incident_type=1, id_user=id_user, created_by=id_user,
                incident_date=abre, close_date=cierra, latitude=latitude, id_proyect=id_proyect,
                incident_status=status or ("abierta" if cierra is None else "resuelta"),
                deletion_date=baja,
            ))
        return self._siguiente_id

    def _marcas(self, consulta, inicio, fin):
        with transaction_context() as db:
            return consulta(db, inicio, fin, {}, None)

    def _foto(self, consulta, fecha_fin):
        with transaction_context() as db:
            filas = consulta(db, fecha_fin - timedelta(days=6), fecha_fin, {}, None)
        return {id_team: (periodo, valor) for id_team, periodo, valor in filas}


class FotosDeChecadasTest(ChecadasBase):
    """`checadas_en_turno_por_equipo` y `checadas_sin_salida_por_equipo`: fotos de AHORA, por antiguedad."""

    def en_turno(self, fecha_fin=D):
        return {id_team: valor for id_team, (_, valor) in self._foto(checadas_en_turno_por_equipo_query, fecha_fin).items()}

    def sin_salida(self, fecha_fin=D):
        return {id_team: valor for id_team, (_, valor) in self._foto(checadas_sin_salida_por_equipo_query, fecha_fin).items()}

    # --- el umbral de 12 horas ----------------------------------------------------------------

    def test_una_checada_abierta_de_menos_de_12_horas_esta_en_turno(self):
        self._checada(ANA, local(D, 10, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 1, SUR: 0, VACIO: 0}, self.en_turno())
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.sin_salida())

    def test_a_exactamente_12_horas_ya_es_sin_salida_y_un_segundo_antes_todavia_esta_en_turno(self):
        self._checada(ANA, local(D, 3, 0, 0))
        with ahora_local(local(D, 14, 59, 59)):
            self.assertEqual(1, self.en_turno()[NORTE], "11 h 59 min 59 s: en turno")
            self.assertEqual(0, self.sin_salida()[NORTE])
        with ahora_local(local(D, 15, 0, 0)):
            self.assertEqual(0, self.en_turno()[NORTE], "12 h exactas: ya no esta en turno")
            self.assertEqual(1, self.sin_salida()[NORTE], "12 h exactas: sin salida")

    def test_el_umbral_es_una_constante_con_nombre(self):
        self.assertEqual(12, UMBRAL_SIN_SALIDA_HORAS)
        self.assertEqual(timedelta(hours=12), checadas.UMBRAL_SIN_SALIDA)
        # La descripcion que ve el gerente cita el mismo numero, no uno escrito a mano.
        for clave in ("checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo"):
            self.assertIn(str(UMBRAL_SIN_SALIDA_HORAS), KPI_POR_CLAVE[clave].descripcion)

    # --- cruzar la medianoche -------------------------------------------------------------------

    def test_una_entrada_de_las_2350_sigue_en_turno_a_las_0010_del_dia_siguiente(self):
        self._checada(ANA, local(D, 23, 50))
        with ahora_local(local(D, 23, 55)):
            self.assertEqual(1, self.en_turno(D)[NORTE])
        # Ya es OTRO dia calendario: la foto de hoy (D1) no se filtra por dia, solo por antiguedad.
        with ahora_local(local(D1, 0, 10)):
            self.assertEqual(1, self.en_turno(D1)[NORTE])
            self.assertEqual(0, self.sin_salida(D1)[NORTE])
        with ahora_local(local(D1, 11, 49)):
            self.assertEqual(1, self.en_turno(D1)[NORTE], "11 h 59 min")
        with ahora_local(local(D1, 11, 50)):
            self.assertEqual(1, self.sin_salida(D1)[NORTE], "12 h exactas desde las 23:50")

    # --- "abierta" es no tener close_date, no un estatus concreto ------------------------------------

    def test_una_checada_en_proceso_cuenta_como_abierta(self):
        # El flujo permite abierta -> en_proceso -> resuelta, y en_proceso no es un estatus de cierre: sin close_date
        # la persona no ha marcado su salida, tenga el estatus que tenga.
        self._checada(ANA, local(D, 10, 0), status="en_proceso")
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(1, self.en_turno()[NORTE])
        with ahora_local(local(D1, 0, 0)):
            self.assertEqual(1, self.sin_salida(D1)[NORTE], "14 h abierta, aunque este en proceso")

    def test_el_ciclo_real_de_la_incidencia_cierra_y_reabre_la_checada(self):
        # Con el servicio de verdad: resolver pone close_date (ya no cuenta) y reabrir la borra (vuelve a contar,
        # con su entrada original).
        creada = IncidentService.create({
            "incident_date": "2026-10-15T10:00:00", "incident_status": "abierta", "id_incident_type": 1,
            "id_user": ANA, "created_by": ANA, "latitude": "21.1161741", "longitude": "-101.6625754", "distance_m": 9,
        })
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(1, self.en_turno()[NORTE], "abierta")
        IncidentService.update(creada["id_incident"], {"incident_status": "resuelta"})
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(0, self.en_turno()[NORTE], "resuelta: tiene close_date")
            self.assertEqual(0, self.sin_salida()[NORTE])
        IncidentService.update(creada["id_incident"], {"incident_status": "en_proceso"})
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(1, self.en_turno()[NORTE], "reabierta: se borro el close_date")

    # --- quien cuenta -----------------------------------------------------------------------------

    def test_una_checada_cerrada_no_cuenta_en_ninguna_foto(self):
        self._checada(ANA, local(D, 3, 0), local(D, 11, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(0, self.en_turno()[NORTE])
            self.assertEqual(0, self.sin_salida()[NORTE])

    def test_una_incidencia_sin_coordenadas_se_excluye(self):
        self._checada(ANA, local(D, 10, 0), latitude=None)
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.en_turno())
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.sin_salida())

    def test_cuenta_personas_distintas_y_no_checadas(self):
        self._checada(ANA, local(D, 9, 0))
        self._checada(ANA, local(D, 10, 0))      # la misma persona, otra checada abierta
        self._checada(BETO, local(D, 11, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(2, self.en_turno()[NORTE], "Ana (una vez) y Beto")

    def test_una_persona_en_dos_equipos_cuenta_en_cada_uno_y_no_hay_total_entre_equipos(self):
        self._checada(BETO, local(D, 10, 0))     # Beto: Norte y Sur
        with ahora_local(local(D, 15, 0)):
            filas = self.en_turno()
        self.assertEqual(1, filas[NORTE])
        self.assertEqual(1, filas[SUR])
        # La consulta solo entrega una fila por equipo: ninguna que sume Norte + Sur (seria contar a Beto dos veces).
        self.assertEqual({NORTE, SUR, VACIO}, set(filas))

    def test_una_persona_sin_equipo_no_aparece_en_ningun_equipo(self):
        self._checada(DIEGO, local(D, 10, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.en_turno())

    def test_una_membresia_o_un_equipo_dados_de_baja_no_cuentan(self):
        self._checada(ELENA, local(D, 10, 0))    # su membresia en Norte esta dada de baja
        self._checada(ANA, local(D, 10, 0))      # Ana tambien esta en un equipo dado de baja
        with ahora_local(local(D, 15, 0)):
            filas = self.en_turno()
        self.assertEqual(1, filas[NORTE], "solo Ana, por su membresia vigente")
        self.assertNotIn(BAJA, filas, "un equipo dado de baja no se emite")

    def test_cada_equipo_vigente_sale_con_su_cero(self):
        # Obligatorio: el upsert solo actualiza lo que la consulta regresa; sin la fila en cero, un equipo que pasa
        # de 3 personas a 0 conservaria el 3 para siempre.
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.en_turno())
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.sin_salida())

    def test_una_checada_de_otro_proyecto_cuenta_igual(self):
        # Como los KPIs de incidencias de siempre: `incident.id_proyect` no interviene (alcance_proyecto=False).
        self._checada(ANA, local(D, 10, 0), id_proyect=PROYECTO_OTRO)
        self._checada(BETO, local(D, 10, 0), id_proyect=None)
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(2, self.en_turno()[NORTE])

    def test_una_incidencia_con_baja_o_cancelada_no_cuenta(self):
        self._checada(ANA, local(D, 10, 0), baja=datetime(2026, 10, 15, 11, 0))
        self._checada(BETO, local(D, 10, 0), status="cancelada")
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.en_turno())

    # --- el dia es el LOCAL, no el de UTC -------------------------------------------------------------

    def test_a_las_18_y_a_las_19_hora_de_mexico_el_dia_es_el_local_aunque_el_dia_utc_ya_cambio(self):
        self._checada(ANA, local(D, 17, 50))
        # 18:00 en Mexico = 00:00 UTC del 16: el dia UTC ya cambio, el de Mexico sigue siendo el 15.
        with reloj_en_utc(datetime(2026, 10, 16, 0, 0)):
            filas = self._foto(checadas_en_turno_por_equipo_query, D)
            self.assertEqual({NORTE: (D, 1), SUR: (D, 0), VACIO: (D, 0)}, filas, "18:00 locales: hoy es el 15")
            self.assertEqual({}, self._foto(checadas_en_turno_por_equipo_query, D1), "el 16 es el dia UTC, no el local")
        # 19:00 en Mexico = 01:00 UTC del 16.
        with reloj_en_utc(datetime(2026, 10, 16, 1, 0)):
            filas = self._foto(checadas_en_turno_por_equipo_query, D)
            self.assertEqual((D, 1), filas[NORTE], "19:00 locales: la entrada de las 17:50 sigue en turno")
            self.assertEqual({}, self._foto(checadas_en_turno_por_equipo_query, D1))
        # Un minuto antes de las 18:00 todavia es el mismo dia en los dos relojes.
        with reloj_en_utc(datetime(2026, 10, 15, 23, 59)):
            self.assertEqual((D, 1), self._foto(checadas_en_turno_por_equipo_query, D)[NORTE])

    def test_la_foto_es_de_ahora_y_no_se_inventa_para_otro_dia(self):
        # Un backfill de un rango pasado no puede guardar "quien esta en turno AHORA" bajo una fecha vieja.
        self._checada(ANA, local(D, 10, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({}, self._foto(checadas_en_turno_por_equipo_query, D - timedelta(days=1)))
            self.assertEqual({}, self._foto(checadas_sin_salida_por_equipo_query, D - timedelta(days=1)))
            self.assertEqual({}, self._foto(checadas_en_turno_por_equipo_query, D1))

    def test_las_filas_van_fechadas_en_la_fecha_pedida_y_ordenadas_por_equipo(self):
        with ahora_local(local(D, 15, 0)):
            with transaction_context() as db:
                filas = checadas_en_turno_por_equipo_query(db, D - timedelta(days=6), D, {}, None)
        self.assertEqual([(NORTE, D, 0), (SUR, D, 0), (VACIO, D, 0)], filas)


class FlujosDeChecadasTest(ChecadasBase):
    """`checadas_entradas_por_equipo` y `checadas_salidas_por_equipo`: marcas por equipo y por dia local."""

    def entradas(self, inicio=D, fin=D1):
        return self._marcas(checadas_entradas_por_equipo_query, inicio, fin)

    def salidas(self, inicio=D, fin=D1):
        return self._marcas(checadas_salidas_por_equipo_query, inicio, fin)

    # --- cruzar la medianoche -------------------------------------------------------------------

    def test_una_entrada_de_las_2350_y_su_salida_de_las_0010_caen_en_dias_distintos(self):
        self._checada(ANA, local(D, 23, 50), local(D1, 0, 10))
        self.assertEqual([(NORTE, D, 1)], self.entradas(), "la entrada es del dia en que se marco")
        self.assertEqual([(NORTE, D1, 1)], self.salidas(), "la salida de las 00:10 es del dia siguiente")
        self.assertEqual([], self.salidas(D, D), "el dia de la entrada todavia no tiene esa salida")
        self.assertEqual([], self.entradas(D1, D1), "ni el dia de la salida tiene esa entrada")

    def test_el_dia_es_la_hora_de_pared_sin_convertir_a_utc(self):
        # 19:30 locales son las 01:30 UTC del dia siguiente: contarla ahi seria el error de las 18:00.
        self._checada(ANA, local(D, 19, 30))
        self._checada(ANA, local(D, 23, 59, 59))
        self._checada(ANA, local(D1, 0, 0, 0))
        self.assertEqual([(NORTE, D, 2), (NORTE, D1, 1)], self.entradas())

    def test_no_depende_del_reloj_de_hoy(self):
        # Son flujos de dias ya ocurridos, no una foto de ahora: el reloj no los cambia.
        self._checada(ANA, local(D, 10, 0), local(D, 18, 0))
        sin_reloj = (self.entradas(), self.salidas())
        with ahora_local(local(date(2030, 1, 1), 3, 0)):
            self.assertEqual(sin_reloj, (self.entradas(), self.salidas()))

    # --- que cuenta ----------------------------------------------------------------------------------

    def test_cuenta_checadas_y_no_personas(self):
        self._checada(ANA, local(D, 8, 0), local(D, 12, 0))
        self._checada(ANA, local(D, 13, 0), local(D, 17, 0))      # dos turnos el mismo dia
        self.assertEqual([(NORTE, D, 2)], self.entradas())
        self.assertEqual([(NORTE, D, 2)], self.salidas())

    def test_una_abierta_es_entrada_pero_todavia_no_es_salida(self):
        self._checada(ANA, local(D, 8, 0))
        self.assertEqual([(NORTE, D, 1)], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_persona_en_dos_equipos_cuenta_en_cada_uno(self):
        self._checada(BETO, local(D, 8, 0), local(D, 16, 0))
        self.assertEqual([(NORTE, D, 1), (SUR, D, 1)], self.entradas())
        self.assertEqual([(NORTE, D, 1), (SUR, D, 1)], self.salidas())

    def test_una_persona_sin_equipo_no_cuenta(self):
        self._checada(DIEGO, local(D, 8, 0), local(D, 16, 0))
        self.assertEqual([], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_incidencia_sin_coordenadas_se_excluye(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), latitude=None)
        self.assertEqual([], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_cancelada_o_con_baja_no_es_ni_entrada_ni_salida(self):
        self._checada(ANA, local(D, 8, 0), local(D, 9, 0), status="cancelada")
        self._checada(ANA, local(D, 10, 0), local(D, 11, 0), baja=datetime(2026, 10, 15, 12, 0))
        self.assertEqual([], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_membresia_o_un_equipo_dados_de_baja_no_cuentan(self):
        self._checada(ELENA, local(D, 8, 0), local(D, 16, 0))     # membresia en Norte dada de baja
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))       # Ana: Norte (vigente) y un equipo dado de baja
        self.assertEqual([(NORTE, D, 1)], self.entradas())
        self.assertEqual([(NORTE, D, 1)], self.salidas())

    def test_una_checada_de_otro_proyecto_cuenta_igual(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), id_proyect=PROYECTO_OTRO)
        self.assertEqual([(NORTE, D, 1)], self.entradas())

    # --- el rango -----------------------------------------------------------------------------------

    def test_solo_salen_los_dias_con_datos_y_dentro_del_rango_incluidos_los_extremos(self):
        dia_anterior = D - timedelta(days=1)
        self._checada(ANA, local(dia_anterior, 8, 0), local(dia_anterior, 16, 0))
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))
        self._checada(ANA, local(D1, 8, 0), local(D1, 16, 0))
        self._checada(ANA, local(D + timedelta(days=2), 8, 0), local(D + timedelta(days=2), 16, 0))
        self.assertEqual([(NORTE, D, 1), (NORTE, D1, 1)], self.entradas(D, D1), "ni el dia anterior ni el posterior")
        self.assertEqual([(NORTE, D1, 1)], self.entradas(D1, D1))
        self.assertEqual([], self.entradas(D + timedelta(days=5), D + timedelta(days=6)))


class HorasTrabajadasTest(ChecadasBase):
    """`horas_trabajadas_por_empleado`: minutos de las checadas CERRADAS, por empleado y por dia de la entrada."""

    def horas(self, inicio=D, fin=D1):
        return self._marcas(horas_trabajadas_por_empleado_query, inicio, fin)

    def test_una_entrada_de_las_2350_y_su_salida_de_las_0010_son_20_minutos_del_dia_de_la_entrada(self):
        self._checada(ANA, local(D, 23, 50), local(D1, 0, 10))
        self.assertEqual([(ANA, D, Decimal("20.00"))], self.horas())
        self.assertEqual([], self.horas(D1, D1), "no se parte en dos dias: el turno es del dia en que empezo")

    def test_suma_los_turnos_del_mismo_dia(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))        # 480
        self._checada(ANA, local(D, 18, 0), local(D, 18, 30))      # 30
        self.assertEqual([(ANA, D, Decimal("510.00"))], self.horas())

    def test_los_segundos_cuentan_como_fraccion_de_minuto(self):
        self._checada(ANA, local(D, 8, 0, 0), local(D, 8, 1, 30))
        self.assertEqual([(ANA, D, Decimal("1.50"))], self.horas())

    def test_una_abierta_todavia_no_suma(self):
        self._checada(ANA, local(D, 8, 0))
        self.assertEqual([], self.horas())

    def test_una_incidencia_sin_coordenadas_cancelada_o_con_baja_no_suma(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), latitude=None)
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), status="cancelada")
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), baja=datetime(2026, 10, 15, 17, 0))
        self.assertEqual([], self.horas())

    def test_una_salida_anterior_a_su_entrada_no_es_un_turno(self):
        self._checada(ANA, local(D, 16, 0), local(D, 8, 0))
        self.assertEqual([], self.horas())

    def test_no_depende_del_equipo_ni_se_duplica_por_estar_en_dos(self):
        self._checada(DIEGO, local(D, 8, 0), local(D, 10, 0))      # sin equipo: suma igual
        self._checada(BETO, local(D, 8, 0), local(D, 9, 0))        # en dos equipos: una sola vez
        self.assertEqual([(BETO, D, Decimal("60.00")), (DIEGO, D, Decimal("120.00"))], self.horas())

    def test_una_checada_de_otro_proyecto_suma_igual(self):
        self._checada(ANA, local(D, 8, 0), local(D, 9, 0), id_proyect=PROYECTO_OTRO)
        self.assertEqual([(ANA, D, Decimal("60.00"))], self.horas())

    def test_el_dia_es_el_de_la_entrada_y_el_rango_incluye_sus_extremos(self):
        dia_anterior = D - timedelta(days=1)
        self._checada(ANA, local(dia_anterior, 23, 50), local(D, 0, 10))   # empezo antes del rango
        self._checada(ANA, local(D, 8, 0), local(D, 9, 0))
        self._checada(ANA, local(D1, 8, 0), local(D1, 10, 0))
        self.assertEqual([(ANA, D, Decimal("60.00")), (ANA, D1, Decimal("120.00"))], self.horas(D, D1))
        self.assertEqual([(ANA, D1, Decimal("120.00"))], self.horas(D1, D1))

    def test_no_depende_del_reloj_de_hoy(self):
        self._checada(ANA, local(D, 8, 0), local(D, 9, 0))
        with ahora_local(local(date(2030, 1, 1), 3, 0)):
            self.assertEqual([(ANA, D, Decimal("60.00"))], self.horas())

    def test_es_un_kpi_por_empleado_en_minutos_de_operaciones(self):
        kpi = KPI_POR_CLAVE["horas_trabajadas_por_empleado"]
        self.assertEqual("operaciones", kpi.modulo)
        self.assertEqual(("empleado",), kpi.dimensiones)
        self.assertEqual("suma", kpi.agregacion)
        self.assertEqual("minutos", kpi.unidad)
        self.assertFalse(kpi.alcance_proyecto)
        self.assertEqual(("barras",), tuple(kpi.graficas_permitidas))
        self.assertEqual("Empleado", kpi.etiqueta_dimension)


@unittest.skipUnless(engine.dialect.name == "postgresql", "El upsert de snapshots usa INSERT ... ON CONFLICT de PostgreSQL")
class CorridaFrecuenteDeChecadasTest(ChecadasBase):
    """La corrida de 5 minutos incluye SOLO las dos fotos de checadas, y el upsert nocturno no las falsifica."""

    def setUp(self):
        super().setUp()
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.ids = dict(db.execute(select(KpiDefinition.clave, KpiDefinition.id_kpi_definition)).all())
        self.fotos = tuple(KPI_POR_CLAVE[c] for c in frecuencia.KPIS_FRECUENTES)

    def _guardado(self, clave):
        """`{periodo: {id_team: valor}}` de lo que hay en `kpi_snapshot` para ese KPI."""
        with transaction_context() as db:
            filas = db.execute(select(KpiSnapshot.periodo, KpiSnapshot.dimension_key, KpiSnapshot.valor).where(
                KpiSnapshot.id_kpi_definition == self.ids[clave])).all()
        guardado: dict = {}
        for periodo, llave, valor in filas:
            guardado.setdefault(periodo, {})[llave["id_team"]] = float(valor)
        return guardado

    def _con_registro(self, kpis):
        return mock.patch.object(tasks_kpis, "KPI_REGISTRY", tuple(kpis))

    def _contenedor_con_fecha(self, hoy):
        # La corrida nocturna fecha con `date.today()` del contenedor; la frecuente, con `hoy_negocio()`.
        falso = mock.MagicMock(wraps=date)
        falso.today.return_value = hoy
        return mock.patch.object(tasks_kpis, "date", falso)

    def _cerrar(self, id_incident, cierre):
        with transaction_context() as db:
            db.get(Incident, id_incident).close_date = cierre

    def test_la_corrida_frecuente_recalcula_las_dos_fotos_y_no_arrastra_al_resto_de_operaciones(self):
        self._checada(ANA, local(D, 10, 0))
        ajenas = []
        for clave in ("incidencias_abiertas_por_empleado", "checadas_entradas_por_equipo", "horas_trabajadas_por_empleado"):
            kpi = copy.copy(KPI_POR_CLAVE[clave])           # del modulo operaciones, igual que las fotos
            self.assertEqual("operaciones", kpi.modulo)
            kpi.query_builder = mock.Mock(return_value=[])
            ajenas.append(kpi)
        de_restaurante = copy.copy(KPI_POR_CLAVE["ventas_restaurante"])     # su modulo si es frecuente
        de_restaurante.query_builder = mock.Mock(return_value=[])
        with self._con_registro((*self.fotos, *ajenas, de_restaurante)), ahora_local(local(D, 15, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        for kpi in ajenas:
            kpi.query_builder.assert_not_called()
        de_restaurante.query_builder.assert_called()
        self.assertEqual(list(frecuencia.KPIS_FRECUENTES), resultado["claves"])
        self.assertEqual(D.isoformat(), resultado["fecha_inicio"])
        self.assertEqual(D.isoformat(), resultado["fecha_fin"])
        self.assertEqual({D: {NORTE: 1.0, SUR: 0.0, VACIO: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0}}, self._guardado("checadas_sin_salida_por_equipo"))

    def test_un_equipo_que_pasa_de_dos_personas_a_cero_no_conserva_el_dos(self):
        a = self._checada(ANA, local(D, 10, 0))
        b = self._checada(BETO, local(D, 11, 0))            # Beto esta en Norte y en Sur
        with self._con_registro(self.fotos), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual({D: {NORTE: 2.0, SUR: 1.0, VACIO: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))
        self._cerrar(a, local(D, 15, 30))
        self._cerrar(b, local(D, 15, 40))
        with self._con_registro(self.fotos), ahora_local(local(D, 16, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        # La MISMA fila (kpi, equipo, dia) se sobrescribe con 0; no queda el 2 viejo ni filas de mas.
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))

    def test_la_nocturna_de_7_dias_solo_escribe_hoy_y_no_pisa_la_foto_de_los_dias_anteriores(self):
        ayer = D - timedelta(days=1)
        self._checada(ANA, local(D, 10, 0))
        with transaction_context() as db:                   # lo que quedo guardado ayer por la corrida frecuente
            db.add(KpiSnapshot(id_kpi_definition=self.ids["checadas_en_turno_por_equipo"], dimension_key={"id_team": NORTE},
                               periodo=ayer, valor=Decimal("5")))
        with self._con_registro(self.fotos), self._contenedor_con_fecha(D), ahora_local(local(D, 19, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual((D - timedelta(days=6)).isoformat(), resultado["fecha_inicio"], "la ventana es de 7 dias")
        guardado = self._guardado("checadas_en_turno_por_equipo")
        self.assertEqual({ayer, D}, set(guardado), "de los 7 dias solo se escribe hoy")
        self.assertEqual({NORTE: 5.0}, guardado[ayer], "la foto de ayer es lo que era ayer: no se reescribe")
        self.assertEqual({NORTE: 1.0, SUR: 0.0, VACIO: 0.0}, guardado[D])

    def test_la_nocturna_de_un_contenedor_en_utc_no_guarda_la_foto_bajo_el_dia_utc(self):
        # 19:00 en Mexico = 01:00 UTC del dia siguiente: el contenedor (UTC) cree que hoy es D1, pero hoy es D.
        # Sin esta guarda, la foto de las 19:00 del dia 15 se guardaria como la del 16.
        self._checada(ANA, local(D, 10, 0))
        with self._con_registro(self.fotos), self._contenedor_con_fecha(D1), reloj_en_utc(datetime(2026, 10, 16, 1, 0)):
            tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual({}, self._guardado("checadas_en_turno_por_equipo"))
        self.assertEqual({}, self._guardado("checadas_sin_salida_por_equipo"))

    def test_un_backfill_de_un_rango_pasado_no_inventa_fotos(self):
        self._checada(ANA, local(D, 10, 0))
        with self._con_registro(self.fotos), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalcular_kpi_snapshots_rango(D - timedelta(days=3), D - timedelta(days=1))
        self.assertEqual({}, self._guardado("checadas_en_turno_por_equipo"))

