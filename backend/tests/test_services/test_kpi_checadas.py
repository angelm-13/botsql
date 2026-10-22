"""KPIs de checadas (entrada/salida) de Comala: filas de `incident` con coordenadas.

Corren en SQLite y en PostgreSQL (solo usan SQL portable). `incident_date` y `close_date` son hora de pared
del negocio, sin zona; "ahora" sale de `ahora_negocio()`, que aqui se congela en un instante UTC concreto y
deja que el codigo real haga la conversion a hora de Mexico (UTC-6 todo el ano desde 2022).
"""

from __future__ import annotations

import copy
import unittest
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest import mock

import jwt
from sqlalchemy import Date, literal, select, text

from app.jobs import tasks_kpis
from app.kpis import frecuencia
from app.kpis.modulos import checadas
from app.kpis.modulos.checadas import (
    TOPE_DURACION_CHECADA_HORAS,
    UMBRAL_SIN_SALIDA_HORAS,
    equipos_de_la_persona_en,
    persona_en_equipos_el_dia,
    checadas_con_duracion_anomala_query,
    checadas_en_turno_por_empleado_query,
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
from app.utils.auth import SECRET_KEY
from app.utils.tiempo import pared_a_utc
from tests.conftest import BackendTestCase
from tests.reloj import ahora_local, reloj_en_utc

# Personas
ANA, BETO, CARLA, DIEGO, ELENA, FRANCO = 101, 102, 103, 104, 105, 106
# Equipos (parques)
NORTE, SUR, VACIO, BAJA = 7001, 7002, 7003, 7004
PROYECTO_OTRO = 2
LATITUD = Decimal("21.1161741")

# Desde cuando estan en su equipo las personas del fixture: antes de cualquier marca de las pruebas.
DESDE = datetime(2026, 1, 1)

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
            for id_user, nombre in ((ANA, "Ana"), (BETO, "Beto"), (CARLA, "Carla"), (DIEGO, "Diego"), (ELENA, "Elena"), (FRANCO, "Franco")):
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
            # Beto esta en DOS equipos; Diego en ninguno; la membresia de Elena en Norte esta dada de baja (sin equipo);
            # Ana tambien esta en un equipo que ya no existe (le basta Norte); Franco SOLO esta en ese equipo que ya no
            # existe (sin equipo vigente). Todas empezaron ANTES de las marcas de las pruebas (`DESDE`): el equipo de una
            # marca es el que la persona tenia en ese momento, no el de hoy.
            for id_team, id_user, baja in (
                (NORTE, ANA, None), (NORTE, BETO, None), (SUR, BETO, None), (SUR, CARLA, None),
                (NORTE, ELENA, datetime(2026, 6, 1)), (BAJA, ANA, None), (BAJA, FRANCO, None),
            ):
                db.add(NmTeamUser(id_team=id_team, id_user=id_user, created_by=1, creation_date=DESDE, deletion_date=baja))
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

    def _por_equipo(self, consulta, fecha_fin):
        # Solo los equipos: la fila "Sin equipo" (entidad None) se mira aparte, con `sin_equipo_*`.
        return {id_team: valor for id_team, (_, valor) in self._foto(consulta, fecha_fin).items() if id_team is not None}

    def en_turno(self, fecha_fin=D):
        return self._por_equipo(checadas_en_turno_por_equipo_query, fecha_fin)

    def sin_salida(self, fecha_fin=D):
        return self._por_equipo(checadas_sin_salida_por_equipo_query, fecha_fin)

    def sin_equipo_en_turno(self, fecha_fin=D):
        return self._foto(checadas_en_turno_por_equipo_query, fecha_fin)[None][1]

    def sin_equipo_sin_salida(self, fecha_fin=D):
        return self._foto(checadas_sin_salida_por_equipo_query, fecha_fin)[None][1]

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

    def test_el_borde_de_12_h_separa_a_varias_personas_a_la_vez_sin_solaparse(self):
        ahora = local(D, 15, 0)
        self._checada(ANA, ahora - timedelta(hours=11, minutes=59, seconds=59))    # Norte
        self._checada(BETO, ahora - timedelta(hours=12))                           # Norte y Sur: 12 h exactas
        self._checada(CARLA, ahora - timedelta(hours=12, seconds=1))               # Sur
        with ahora_local(ahora):
            self.assertEqual({NORTE: 1, SUR: 0, VACIO: 0}, self.en_turno(), "solo Ana esta en turno")
            self.assertEqual({NORTE: 1, SUR: 2, VACIO: 0}, self.sin_salida(), "Beto (12 h exactas, en sus dos equipos) y Carla")

    def test_el_borde_de_12_h_cruzando_la_medianoche(self):
        # A las 08:00 del dia siguiente: la de las 20:00 lleva 12 h exactas (sin salida) y la de las 20:00:01 un segundo menos (en turno).
        self._checada(ANA, local(D, 20, 0, 0))              # Norte
        self._checada(CARLA, local(D, 20, 0, 1))            # Sur
        with ahora_local(local(D1, 8, 0, 0)):
            self.assertEqual({NORTE: 0, SUR: 1, VACIO: 0}, self.en_turno(D1))
            self.assertEqual({NORTE: 1, SUR: 0, VACIO: 0}, self.sin_salida(D1))

    def test_el_borde_de_12_h_tambien_separa_a_quien_no_tiene_equipo(self):
        ahora = local(D, 15, 0)
        self._checada(DIEGO, ahora - timedelta(hours=11, minutes=59, seconds=59))
        self._checada(FRANCO, ahora - timedelta(hours=12))                         # solo esta en un equipo dado de baja: sin equipo
        with ahora_local(ahora):
            self.assertEqual(1, self.sin_equipo_en_turno(), "Diego")
            self.assertEqual(1, self.sin_equipo_sin_salida(), "Franco, con 12 h exactas")

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

    def test_una_persona_sin_equipo_sale_en_sin_equipo_y_en_ningun_equipo(self):
        self._checada(DIEGO, local(D, 10, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0}, self.en_turno())
            self.assertEqual(1, self.sin_equipo_en_turno())
            self.assertEqual(0, self.sin_equipo_sin_salida())
        with ahora_local(local(D1, 0, 0)):                 # 14 h abierta
            self.assertEqual(0, self.sin_equipo_en_turno(D1))
            self.assertEqual(1, self.sin_equipo_sin_salida(D1))

    def test_quien_tiene_equipo_no_cuenta_en_sin_equipo(self):
        self._checada(ANA, local(D, 10, 0))      # Norte
        self._checada(CARLA, local(D, 10, 0))    # Sur
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 1, SUR: 1, VACIO: 0}, self.en_turno())
            self.assertEqual(0, self.sin_equipo_en_turno())

    def test_una_persona_en_dos_equipos_cuenta_en_cada_uno_y_no_en_sin_equipo(self):
        self._checada(BETO, local(D, 10, 0))     # Norte y Sur
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({NORTE: 1, SUR: 1, VACIO: 0}, self.en_turno())
            self.assertEqual(0, self.sin_equipo_en_turno())

    def test_sin_equipo_son_personas_distintas_y_respeta_las_mismas_reglas_que_los_equipos(self):
        self._checada(DIEGO, local(D, 9, 0))
        self._checada(DIEGO, local(D, 10, 0))                                  # la misma persona dos veces: una
        self._checada(DIEGO, local(D, 11, 0), local(D, 12, 0))                 # cerrada: no cuenta
        self._checada(DIEGO, local(D, 11, 0), status="cancelada")              # cancelada: no cuenta
        self._checada(DIEGO, local(D, 11, 0), latitude=None)                   # sin coordenadas: no cuenta
        self._checada(DIEGO, local(D, 11, 0), baja=datetime(2026, 10, 15, 12, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(1, self.sin_equipo_en_turno())

    def test_sin_equipo_es_tambien_quien_solo_tiene_membresias_o_equipos_dados_de_baja(self):
        self._checada(ELENA, local(D, 10, 0))    # su unica membresia (Norte) esta dada de baja
        self._checada(FRANCO, local(D, 10, 0))   # su unico equipo esta dado de baja
        self._checada(ANA, local(D, 10, 0))      # Norte vigente (aunque tambien este en un equipo dado de baja)
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(2, self.sin_equipo_en_turno(), "Elena y Franco")
            self.assertEqual(1, self.en_turno()[NORTE], "solo Ana")
            self.assertNotIn(BAJA, self.en_turno(), "un equipo dado de baja no se emite")

    def test_la_fila_sin_equipo_sale_siempre_con_su_cero(self):
        # Igual que cada equipo: sin la fila en cero, un "Sin equipo" que baja a 0 conservaria el valor viejo.
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(0, self.sin_equipo_en_turno())
            self.assertEqual(0, self.sin_equipo_sin_salida())

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
            self.assertEqual({NORTE: (D, 1), SUR: (D, 0), VACIO: (D, 0), None: (D, 0)}, filas, "18:00 locales: hoy es el 15")
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
        self.assertEqual([(NORTE, D, 0), (SUR, D, 0), (VACIO, D, 0), (None, D, 0)], filas, "los equipos por id y al final Sin equipo")


class EnTurnoPorEmpleadoTest(ChecadasBase):
    """`checadas_en_turno_por_empleado`: foto con los minutos que lleva en turno cada persona."""

    def foto(self, fecha_fin=D):
        with transaction_context() as db:
            filas = checadas_en_turno_por_empleado_query(db, fecha_fin - timedelta(days=6), fecha_fin, {}, None)
        return {id_user: valor for id_user, _, valor in filas}

    # --- los minutos y el umbral de 12 horas ---------------------------------------------------------

    def test_una_abierta_de_2_horas_son_120_minutos(self):
        self._checada(ANA, local(D, 13, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("120.00"), self.foto()[ANA])

    def test_una_abierta_de_11_h_59_min_sigue_en_turno(self):
        self._checada(ANA, local(D, 3, 1))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("719.00"), self.foto()[ANA])

    def test_a_exactamente_12_horas_ya_no_esta_en_turno_y_queda_en_cero(self):
        self._checada(ANA, local(D, 3, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("0.00"), self.foto()[ANA], "12 h exactas: sin salida, no en turno")

    def test_el_borde_de_12_h_con_varias_personas_a_la_vez(self):
        ahora = local(D, 15, 0)
        self._checada(ANA, ahora - timedelta(hours=11, minutes=59, seconds=59))
        self._checada(BETO, ahora - timedelta(hours=12))
        self._checada(CARLA, ahora - timedelta(hours=12, seconds=1))
        with ahora_local(ahora):
            foto = self.foto()
        self.assertEqual(Decimal("719.98"), foto[ANA], "11 h 59 min 59 s: sigue en turno")
        self.assertEqual(Decimal("0.00"), foto[BETO], "12 h exactas: fuera de turno")
        self.assertEqual(Decimal("0.00"), foto[CARLA], "12 h y un segundo: fuera de turno")

    def test_el_borde_de_12_h_cruzando_la_medianoche(self):
        self._checada(ANA, local(D, 20, 0, 0))              # a las 08:00 del dia siguiente: 12 h exactas
        self._checada(CARLA, local(D, 20, 0, 1))            # un segundo menos
        with ahora_local(local(D1, 8, 0, 0)):
            foto = self.foto(D1)
        self.assertEqual(Decimal("0.00"), foto[ANA])
        self.assertEqual(Decimal("719.98"), foto[CARLA])

    def test_las_tres_consultas_coinciden_en_quien_esta_en_turno_en_el_borde_de_12_h(self):
        # El KPI por persona y las dos fotos por equipo comparten el corte de 12 h: nadie puede estar en turno en una y sin salida en otra.
        ahora = local(D, 15, 0)
        self._checada(ANA, ahora - timedelta(hours=11, minutes=59, seconds=59))    # Norte, en turno
        self._checada(BETO, ahora - timedelta(hours=12))                           # Norte y Sur, sin salida
        self._checada(DIEGO, ahora - timedelta(hours=11, minutes=59, seconds=59))  # sin equipo, en turno
        self._checada(FRANCO, ahora - timedelta(hours=12))                         # sin equipo, sin salida
        with ahora_local(ahora):
            en_turno_por_persona = {u for u, minutos in self.foto().items() if minutos > 0}
            en_turno = {id_team: valor for id_team, (_, valor) in self._foto(checadas_en_turno_por_equipo_query, D).items()}
            sin_salida = {id_team: valor for id_team, (_, valor) in self._foto(checadas_sin_salida_por_equipo_query, D).items()}
        self.assertEqual({ANA, DIEGO}, en_turno_por_persona)
        self.assertEqual({NORTE: 1, SUR: 0, VACIO: 0, None: 1}, en_turno)
        self.assertEqual({NORTE: 1, SUR: 1, VACIO: 0, None: 1}, sin_salida)

    def test_una_entrada_que_cruza_la_medianoche_sigue_contando_sus_minutos(self):
        self._checada(ANA, local(D, 23, 50))
        with ahora_local(local(D1, 0, 10)):
            self.assertEqual(Decimal("20.00"), self.foto(D1)[ANA])

    def test_los_segundos_son_fraccion_de_minuto(self):
        self._checada(ANA, local(D, 14, 58, 30))
        with ahora_local(local(D, 15, 0, 0)):
            self.assertEqual(Decimal("1.50"), self.foto()[ANA])

    # --- quien cuenta -------------------------------------------------------------------------------------

    def test_una_checada_cerrada_deja_a_la_persona_en_cero(self):
        self._checada(ANA, local(D, 10, 0), local(D, 12, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("0.00"), self.foto()[ANA])

    def test_una_incidencia_sin_coordenadas_no_es_checada_y_no_genera_fila(self):
        self._checada(ANA, local(D, 13, 0), latitude=None)
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({}, self.foto())

    def test_con_dos_abiertas_cuenta_la_mas_reciente(self):
        self._checada(ANA, local(D, 9, 0))     # 6 h
        self._checada(ANA, local(D, 12, 0))    # 3 h: la que esta en curso
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("180.00"), self.foto()[ANA])

    def test_una_abierta_de_12_horas_o_mas_no_le_gana_a_una_reciente_ni_cuenta_sola(self):
        self._checada(ANA, local(D, 1, 0))      # 14 h: sin salida
        self._checada(BETO, local(D, 1, 0))     # 14 h: sin salida, y es la unica
        self._checada(ANA, local(D, 14, 0))     # 1 h: en curso
        with ahora_local(local(D, 15, 0)):
            foto = self.foto()
        self.assertEqual(Decimal("60.00"), foto[ANA])
        self.assertEqual(Decimal("0.00"), foto[BETO], "solo tiene una de 14 h: no esta en turno")

    def test_una_en_proceso_cuenta_como_abierta(self):
        self._checada(ANA, local(D, 13, 0), status="en_proceso")
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("120.00"), self.foto()[ANA])

    def test_cualquier_persona_cuenta_tenga_equipo_o_no_y_sin_importar_el_proyecto(self):
        self._checada(DIEGO, local(D, 14, 0))                              # sin equipo
        self._checada(BETO, local(D, 14, 0), id_proyect=PROYECTO_OTRO)     # en dos equipos: una sola fila
        with ahora_local(local(D, 15, 0)):
            foto = self.foto()
        self.assertEqual({DIEGO: Decimal("60.00"), BETO: Decimal("60.00")}, foto)

    # --- los ceros: que un valor viejo no se quede pegado --------------------------------------------------

    def test_quien_ya_no_esta_en_turno_sigue_saliendo_con_cero(self):
        # Por la tarde Ana llevaba 3 h en turno; por la noche cerro. La consulta de la noche la devuelve en CERO (el
        # upsert la pisa); sin esa fila su valor de la tarde se quedaria pegado.
        id_ana = self._checada(ANA, local(D, 12, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual(Decimal("180.00"), self.foto()[ANA])
        with transaction_context() as db:
            db.get(Incident, id_ana).close_date = local(D, 16, 0)
        with ahora_local(local(D, 20, 0)):
            self.assertEqual({ANA: Decimal("0.00")}, self.foto())

    def test_una_checada_cancelada_o_borrada_despues_de_contar_tambien_deja_a_la_persona_en_cero(self):
        # Los candidatos se calculan SIN mirar la cancelacion ni la baja: si no, quien se anulo despues de contar
        # desapareceria de la consulta y conservaria su valor.
        self._checada(ANA, local(D, 13, 0), status="cancelada")
        self._checada(BETO, local(D, 13, 0), baja=datetime(2026, 10, 15, 14, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({ANA: Decimal("0.00"), BETO: Decimal("0.00")}, self.foto())

    def test_solo_salen_quienes_pudieron_estar_en_turno_hoy(self):
        # Pudo estar en turno hoy quien entro desde 12 horas antes de las 00:00: desde ayer a las 12:00.
        self._checada(ANA, local(D - timedelta(days=1), 12, 0), local(D - timedelta(days=1), 20, 0))     # candidata
        self._checada(CARLA, local(D - timedelta(days=1), 11, 59), local(D - timedelta(days=1), 20, 0))  # ya no
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({ANA: Decimal("0.00")}, self.foto())

    # --- el dia es el local y es una foto de ahora -------------------------------------------------------

    def test_a_las_18_y_a_las_19_hora_de_mexico_el_dia_es_el_local(self):
        self._checada(ANA, local(D, 17, 50))
        with reloj_en_utc(datetime(2026, 10, 16, 0, 0)):                      # 18:00 en Mexico
            self.assertEqual({ANA: Decimal("10.00")}, self.foto(D))
            self.assertEqual({}, self.foto(D1), "el 16 es el dia UTC, no el local")
        with reloj_en_utc(datetime(2026, 10, 16, 1, 0)):                      # 19:00 en Mexico
            self.assertEqual({ANA: Decimal("70.00")}, self.foto(D))
            self.assertEqual({}, self.foto(D1))

    def test_no_se_inventa_una_foto_para_otro_dia(self):
        self._checada(ANA, local(D, 13, 0))
        with ahora_local(local(D, 15, 0)):
            self.assertEqual({}, self.foto(D - timedelta(days=1)))
            self.assertEqual({}, self.foto(D1))


class FlujosDeChecadasTest(ChecadasBase):
    """`checadas_entradas_por_equipo` y `checadas_salidas_por_equipo`: marcas por equipo y por dia local."""

    def entradas_todas(self, inicio=D, fin=D1):
        return self._marcas(checadas_entradas_por_equipo_query, inicio, fin)

    def salidas_todas(self, inicio=D, fin=D1):
        return self._marcas(checadas_salidas_por_equipo_query, inicio, fin)

    # Solo lo que tiene marcas, por equipo (sin los ceros ni la fila "Sin equipo"): lo que miran casi todas las pruebas.
    def entradas(self, inicio=D, fin=D1):
        return [f for f in self.entradas_todas(inicio, fin) if f[0] is not None and f[2]]

    def salidas(self, inicio=D, fin=D1):
        return [f for f in self.salidas_todas(inicio, fin) if f[0] is not None and f[2]]

    # La fila "Sin equipo" (entidad None): `[(dia, marcas)]` de los dias que tienen alguna.
    def entradas_sin_equipo(self, inicio=D, fin=D1):
        return [(f[1], f[2]) for f in self.entradas_todas(inicio, fin) if f[0] is None and f[2]]

    def salidas_sin_equipo(self, inicio=D, fin=D1):
        return [(f[1], f[2]) for f in self.salidas_todas(inicio, fin) if f[0] is None and f[2]]

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

    def test_una_persona_sin_equipo_sale_en_sin_equipo_y_en_ningun_equipo(self):
        self._checada(DIEGO, local(D, 8, 0), local(D, 16, 0))
        self.assertEqual([], self.entradas(), "no cuenta en ningun equipo")
        self.assertEqual([], self.salidas())
        self.assertEqual([(D, 1)], self.entradas_sin_equipo())
        self.assertEqual([(D, 1)], self.salidas_sin_equipo())

    def test_quien_tiene_equipo_no_cuenta_en_sin_equipo_y_quien_esta_en_dos_cuenta_en_cada_uno(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))      # Norte
        self._checada(BETO, local(D, 8, 0), local(D, 16, 0))     # Norte y Sur
        self.assertEqual([(NORTE, D, 2), (SUR, D, 1)], self.entradas())
        self.assertEqual([], self.entradas_sin_equipo())
        self.assertEqual([], self.salidas_sin_equipo())

    def test_sin_equipo_incluye_membresias_y_equipos_dados_de_baja_y_cuenta_checadas(self):
        self._checada(ELENA, local(D, 8, 0), local(D, 12, 0))    # su unica membresia esta dada de baja
        self._checada(FRANCO, local(D, 9, 0), local(D, 13, 0))   # su unico equipo esta dado de baja
        self._checada(DIEGO, local(D, 10, 0), local(D, 14, 0))   # nunca tuvo equipo
        self._checada(DIEGO, local(D, 15, 0), local(D, 17, 0))   # dos turnos: son dos entradas
        self.assertEqual([(D, 4)], self.entradas_sin_equipo())
        self.assertEqual([(D, 4)], self.salidas_sin_equipo())

    def test_sin_equipo_respeta_las_mismas_reglas_que_los_equipos(self):
        self._checada(DIEGO, local(D, 8, 0), local(D, 16, 0), latitude=None)
        self._checada(DIEGO, local(D, 8, 0), local(D, 16, 0), status="cancelada")
        self._checada(DIEGO, local(D, 8, 0), local(D, 16, 0), baja=datetime(2026, 10, 15, 17, 0))
        self._checada(DIEGO, local(D, 8, 0))                      # abierta: entrada, pero todavia no salida
        self.assertEqual([(D, 1)], self.entradas_sin_equipo())
        self.assertEqual([], self.salidas_sin_equipo())

    def test_cada_equipo_vigente_y_sin_equipo_salen_con_su_cero_cada_dia_del_rango(self):
        # Obligatorio: el upsert solo actualiza lo que la consulta devuelve. Sin los ceros, un dia que se queda sin
        # marcas (se cancelo la unica) conservaria el valor viejo.
        D2 = D + timedelta(days=2)
        esperado = (
            [(id_team, dia, 0) for id_team in (NORTE, SUR, VACIO) for dia in (D, D1, D2)]
            + [(None, dia, 0) for dia in (D, D1, D2)]
        )
        self.assertEqual(esperado, self.entradas_todas(D, D2), "sin checadas: todo en cero, y no sale el equipo dado de baja")
        self.assertEqual(esperado, self.salidas_todas(D, D2))

    def test_un_dia_con_marcas_y_otro_sin_ellas_mezclan_valores_y_ceros(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))
        filas = self.entradas_todas(D, D1)
        self.assertEqual(1, dict(((t, d), n) for t, d, n in filas)[(NORTE, D)])
        self.assertEqual(0, dict(((t, d), n) for t, d, n in filas)[(NORTE, D1)])
        self.assertEqual(0, dict(((t, d), n) for t, d, n in filas)[(None, D)])

    def test_una_incidencia_sin_coordenadas_se_excluye(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0), latitude=None)
        self.assertEqual([], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_cancelada_o_con_baja_no_es_ni_entrada_ni_salida(self):
        self._checada(ANA, local(D, 8, 0), local(D, 9, 0), status="cancelada")
        self._checada(ANA, local(D, 10, 0), local(D, 11, 0), baja=datetime(2026, 10, 15, 12, 0))
        self.assertEqual([], self.entradas())
        self.assertEqual([], self.salidas())

    def test_una_membresia_o_un_equipo_dados_de_baja_no_cuentan_como_equipo(self):
        self._checada(ELENA, local(D, 8, 0), local(D, 16, 0))     # membresia en Norte dada de baja
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))       # Ana: Norte (vigente) y un equipo dado de baja
        self.assertEqual([(NORTE, D, 1)], self.entradas(), "solo Ana")
        self.assertEqual([(NORTE, D, 1)], self.salidas())
        self.assertEqual([(D, 1)], self.entradas_sin_equipo(), "Elena")

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

    # --- el tope de 16 horas ------------------------------------------------------------------

    def test_el_tope_es_una_constante_con_nombre(self):
        self.assertEqual(16, TOPE_DURACION_CHECADA_HORAS)

    def test_15_h_59_min_y_16_h_exactas_suman_y_16_h_1_min_no(self):
        self._checada(ANA, local(D, 0, 0), local(D, 15, 59))               # 15 h 59 min
        self._checada(BETO, local(D, 0, 0), local(D, 16, 0))               # 16 h exactas: SI cuenta
        self._checada(CARLA, local(D, 0, 0), local(D, 16, 1))              # 16 h 1 min: no
        self.assertEqual([(ANA, D, Decimal("959.00")), (BETO, D, Decimal("960.00"))], self.horas())

    def test_un_segundo_por_encima_del_tope_ya_no_suma(self):
        self._checada(ANA, local(D, 0, 0, 0), local(D, 16, 0, 0))
        self._checada(BETO, local(D, 0, 0, 0), local(D, 16, 0, 1))
        self.assertEqual([(ANA, D, Decimal("960.00"))], self.horas())

    def test_una_cerrada_al_dia_siguiente_cuenta_en_el_dia_de_la_entrada_si_no_pasa_el_tope(self):
        self._checada(ANA, local(D, 12, 0), local(D1, 4, 0))               # 16 h exactas, cruza la medianoche
        self._checada(BETO, local(D, 20, 0), local(D1, 11, 59))            # 15 h 59 min
        self.assertEqual([(ANA, D, Decimal("960.00")), (BETO, D, Decimal("959.00"))], self.horas())
        self.assertEqual([], self.horas(D1, D1), "el dia de la salida no suma: es el de la entrada")

    def test_una_cerrada_al_dia_siguiente_que_pasa_el_tope_no_suma_en_ningun_dia(self):
        self._checada(ANA, local(D, 8, 0), local(D1, 8, 0))                # 24 h
        self.assertEqual([], self.horas(D, D1))

    def test_una_cerrada_despues_de_mas_de_7_dias_no_suma_en_ningun_dia(self):
        self._checada(ANA, local(D - timedelta(days=10), 8, 0), local(D, 9, 0))
        self.assertEqual([], self.horas(D - timedelta(days=10), D))

    def test_la_anomala_no_arrastra_a_las_demas_checadas_del_mismo_dia(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))                # 480
        self._checada(ANA, local(D, 17, 0), local(D1, 14, 0))              # 21 h: fuera
        self.assertEqual([(ANA, D, Decimal("480.00"))], self.horas())

    def test_una_anomala_cancelada_o_sin_coordenadas_sigue_sin_sumar(self):
        self._checada(ANA, local(D, 0, 0), local(D1, 0, 0), status="cancelada")
        self._checada(BETO, local(D, 0, 0), local(D1, 0, 0), latitude=None)
        self.assertEqual([], self.horas(D, D1))

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


class DuracionAnomalaTest(ChecadasBase):
    """`checadas_con_duracion_anomala`: cerradas con MAS de 16 h, por empleado y por dia de la SALIDA."""

    def anomalas(self, inicio=D, fin=D1):
        return self._marcas(checadas_con_duracion_anomala_query, inicio, fin)

    def test_15_h_59_min_y_16_h_exactas_no_son_anomalas_y_16_h_1_min_si(self):
        self._checada(ANA, local(D, 0, 0), local(D, 15, 59))
        self._checada(BETO, local(D, 0, 0), local(D, 16, 0))               # 16 h exactas: no es anomala
        self._checada(CARLA, local(D, 0, 0), local(D, 16, 1))
        self.assertEqual([(CARLA, D, 1)], self.anomalas())

    def test_un_segundo_por_encima_del_tope_ya_es_anomala(self):
        self._checada(ANA, local(D, 0, 0, 0), local(D, 16, 0, 0))
        self._checada(BETO, local(D, 0, 0, 0), local(D, 16, 0, 1))
        self.assertEqual([(BETO, D, 1)], self.anomalas())

    def test_una_cerrada_al_dia_siguiente_cuenta_en_el_dia_de_la_salida_no_en_el_de_la_entrada(self):
        self._checada(ANA, local(D, 8, 0), local(D1, 8, 0))                # 24 h
        self.assertEqual([(ANA, D1, 1)], self.anomalas(D, D1))
        self.assertEqual([], self.anomalas(D, D), "el dia de la entrada no la ve: es del dia de la salida")

    def test_una_cerrada_al_dia_siguiente_dentro_del_tope_no_es_anomala(self):
        self._checada(ANA, local(D, 22, 0), local(D1, 6, 0))               # 8 h
        self._checada(BETO, local(D, 12, 0), local(D1, 4, 0))              # 16 h exactas
        self.assertEqual([], self.anomalas())

    def test_una_cerrada_despues_de_mas_de_7_dias_aparece_el_dia_de_la_captura(self):
        entrada = D - timedelta(days=10)
        self._checada(ANA, local(entrada, 8, 0), local(D, 9, 0))
        # La ventana de la corrida nocturna (7 dias terminando hoy) ya no alcanza la entrada, pero si la salida.
        self.assertEqual([(ANA, D, 1)], self.anomalas(D - timedelta(days=6), D))
        self.assertEqual([], self.anomalas(entrada, entrada), "el dia de la entrada no la ve")
        # Y es justo la que las horas dejan fuera, en cualquier dia.
        self.assertEqual([], self._marcas(horas_trabajadas_por_empleado_query, entrada, D))

    def test_una_abierta_no_es_anomala_por_vieja_que_sea(self):
        self._checada(ANA, local(D - timedelta(days=3), 8, 0))
        self.assertEqual([], self.anomalas(D - timedelta(days=3), D1))

    def test_una_cancelada_con_baja_o_sin_coordenadas_no_cuenta(self):
        self._checada(ANA, local(D, 0, 0), local(D1, 0, 0), status="cancelada")
        self._checada(BETO, local(D, 0, 0), local(D1, 0, 0), baja=datetime(2026, 10, 16, 9, 0))
        self._checada(CARLA, local(D, 0, 0), local(D1, 0, 0), latitude=None)
        self.assertEqual([], self.anomalas())

    def test_una_salida_anterior_a_su_entrada_no_es_anomala(self):
        self._checada(ANA, local(D1, 8, 0), local(D, 8, 0))
        self.assertEqual([], self.anomalas())

    def test_cruce_de_medianoche_solo_es_anomalo_si_pasa_el_tope(self):
        self._checada(ANA, local(D, 23, 50), local(D1, 0, 10))             # 20 min: no
        self._checada(BETO, local(D, 23, 0), local(D1, 16, 30))            # 17 h 30 min: si, y el dia es el de la salida
        self.assertEqual([(BETO, D1, 1)], self.anomalas())

    def test_el_dia_es_la_hora_de_pared_de_la_salida_sin_convertir_a_utc(self):
        self._checada(ANA, local(D, 1, 0), local(D, 23, 30))               # 22 h 30 min, salida a las 23:30 locales
        self.assertEqual([(ANA, D, 1)], self.anomalas())

    def test_cuenta_checadas_y_no_personas_y_separa_empleados_y_dias(self):
        self._checada(ANA, local(D, 0, 0), local(D, 17, 0))
        self._checada(ANA, local(D, 0, 30), local(D, 18, 0))               # segunda anomalia de Ana el mismo dia: son 2
        self._checada(ANA, local(D, 0, 0), local(D1, 17, 0))               # y una de otro dia
        self._checada(BETO, local(D, 0, 0), local(D, 20, 0))
        self.assertEqual([(ANA, D, 2), (ANA, D1, 1), (BETO, D, 1)], self.anomalas())

    def test_no_depende_del_equipo_ni_se_duplica_por_estar_en_dos(self):
        self._checada(DIEGO, local(D, 0, 0), local(D, 20, 0))              # sin equipo: cuenta igual
        self._checada(BETO, local(D, 0, 0), local(D, 20, 0))               # en dos equipos: una sola vez
        self.assertEqual([(BETO, D, 1), (DIEGO, D, 1)], self.anomalas())

    def test_una_checada_de_otro_proyecto_cuenta_igual(self):
        self._checada(ANA, local(D, 0, 0), local(D, 20, 0), id_proyect=PROYECTO_OTRO)
        self.assertEqual([(ANA, D, 1)], self.anomalas())

    def test_el_rango_incluye_sus_extremos(self):
        self._checada(ANA, local(D - timedelta(days=1), 0, 0), local(D - timedelta(days=1), 20, 0))
        self._checada(ANA, local(D, 0, 0), local(D, 20, 0))
        self._checada(ANA, local(D1, 0, 0), local(D1, 20, 0))
        self.assertEqual([(ANA, D, 1), (ANA, D1, 1)], self.anomalas(D, D1))
        self.assertEqual([(ANA, D1, 1)], self.anomalas(D1, D1))

    def test_no_depende_del_reloj_de_hoy(self):
        self._checada(ANA, local(D, 0, 0), local(D, 20, 0))
        with ahora_local(local(date(2030, 1, 1), 3, 0)):
            self.assertEqual([(ANA, D, 1)], self.anomalas())

    def test_lo_que_las_horas_dejan_fuera_es_exactamente_lo_que_las_anomalias_cuentan(self):
        self._checada(ANA, local(D, 8, 0), local(D, 16, 0))                # 8 h: horas, no anomalia
        self._checada(ANA, local(D, 17, 0), local(D1, 14, 0))              # 21 h: anomalia, no horas
        self.assertEqual([(ANA, D, Decimal("480.00"))], self._marcas(horas_trabajadas_por_empleado_query, D, D1))
        self.assertEqual([(ANA, D1, 1)], self.anomalas())


@unittest.skipUnless(engine.dialect.name == "postgresql", "El upsert de snapshots usa INSERT ... ON CONFLICT de PostgreSQL")
class CorridaFrecuenteDeChecadasTest(ChecadasBase):
    """La corrida de 5 minutos incluye SOLO los KPIs de KPIS_FRECUENTES, y el upsert nocturno no falsifica las fotos."""

    def setUp(self):
        super().setUp()
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.ids = dict(db.execute(select(KpiDefinition.clave, KpiDefinition.id_kpi_definition)).all())
        self.frecuentes = tuple(KPI_POR_CLAVE[c] for c in frecuencia.KPIS_FRECUENTES)   # los cinco

    def _guardado(self, clave, entidad="id_team"):
        """`{periodo: {id_team|id_user: valor}}` de lo que hay en `kpi_snapshot` para ese KPI."""
        with transaction_context() as db:
            filas = db.execute(select(KpiSnapshot.periodo, KpiSnapshot.dimension_key, KpiSnapshot.valor).where(
                KpiSnapshot.id_kpi_definition == self.ids[clave])).all()
        guardado: dict = {}
        for periodo, llave, valor in filas:
            guardado.setdefault(periodo, {})[llave[entidad]] = float(valor)
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

    def test_la_corrida_frecuente_recalcula_sus_cinco_kpis_y_no_arrastra_al_resto_de_operaciones(self):
        self._checada(ANA, local(D, 10, 0))
        ajenas = []
        for clave in ("incidencias_abiertas_por_empleado", "horas_trabajadas_por_empleado"):
            kpi = copy.copy(KPI_POR_CLAVE[clave])           # del modulo operaciones, igual que los de checadas
            self.assertEqual("operaciones", kpi.modulo)
            kpi.query_builder = mock.Mock(return_value=[])
            ajenas.append(kpi)
        de_restaurante = copy.copy(KPI_POR_CLAVE["ventas_restaurante"])     # su modulo si es frecuente
        de_restaurante.query_builder = mock.Mock(return_value=[])
        with self._con_registro((*self.frecuentes, *ajenas, de_restaurante)), ahora_local(local(D, 15, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        for kpi in ajenas:
            kpi.query_builder.assert_not_called()
        de_restaurante.query_builder.assert_called()
        self.assertEqual(list(frecuencia.KPIS_FRECUENTES), resultado["claves"])
        self.assertEqual(D.isoformat(), resultado["fecha_inicio"])
        self.assertEqual(D.isoformat(), resultado["fecha_fin"])
        self.assertEqual({D: {NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_sin_salida_por_equipo"))
        # Y los tres que llegaron con esta ampliacion: entradas de hoy, salidas de hoy y minutos por persona.
        self.assertEqual({D: {NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_entradas_por_equipo"))
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_salidas_por_equipo"))
        self.assertEqual({D: {ANA: 300.0}}, self._guardado("checadas_en_turno_por_empleado", "id_user"))

    def test_un_equipo_que_pasa_de_dos_personas_a_cero_no_conserva_el_dos(self):
        a = self._checada(ANA, local(D, 10, 0))
        b = self._checada(BETO, local(D, 11, 0))            # Beto esta en Norte y en Sur
        with self._con_registro(self.frecuentes), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual({D: {NORTE: 2.0, SUR: 1.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))
        self._cerrar(a, local(D, 15, 30))
        self._cerrar(b, local(D, 15, 40))
        with self._con_registro(self.frecuentes), ahora_local(local(D, 16, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        # La MISMA fila (kpi, equipo, dia) se sobrescribe con 0; no queda el 2 viejo ni filas de mas.
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_en_turno_por_equipo"))

    def test_la_nocturna_de_7_dias_solo_escribe_hoy_y_no_pisa_la_foto_de_los_dias_anteriores(self):
        ayer = D - timedelta(days=1)
        self._checada(ANA, local(D, 10, 0))
        with transaction_context() as db:                   # lo que quedo guardado ayer por la corrida frecuente
            db.add(KpiSnapshot(id_kpi_definition=self.ids["checadas_en_turno_por_equipo"], dimension_key={"id_team": NORTE},
                               periodo=ayer, valor=Decimal("5")))
        with self._con_registro(self.frecuentes), self._contenedor_con_fecha(D), ahora_local(local(D, 19, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual((D - timedelta(days=6)).isoformat(), resultado["fecha_inicio"], "la ventana es de 7 dias")
        guardado = self._guardado("checadas_en_turno_por_equipo")
        self.assertEqual({ayer, D}, set(guardado), "de los 7 dias solo se escribe hoy")
        self.assertEqual({NORTE: 5.0}, guardado[ayer], "la foto de ayer es lo que era ayer: no se reescribe")
        self.assertEqual({NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}, guardado[D])

    def test_la_nocturna_de_un_contenedor_en_utc_no_guarda_la_foto_bajo_el_dia_utc(self):
        # 19:00 en Mexico = 01:00 UTC del dia siguiente: el contenedor (UTC) cree que hoy es D1, pero hoy es D.
        # Sin esta guarda, la foto de las 19:00 del dia 15 se guardaria como la del 16.
        self._checada(ANA, local(D, 10, 0))
        with self._con_registro(self.frecuentes), self._contenedor_con_fecha(D1), reloj_en_utc(datetime(2026, 10, 16, 1, 0)):
            tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual({}, self._guardado("checadas_en_turno_por_equipo"))
        self.assertEqual({}, self._guardado("checadas_sin_salida_por_equipo"))

    def test_un_backfill_de_un_rango_pasado_no_inventa_fotos(self):
        self._checada(ANA, local(D, 10, 0))
        with self._con_registro(self.frecuentes), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalcular_kpi_snapshots_rango(D - timedelta(days=3), D - timedelta(days=1))
        self.assertEqual({}, self._guardado("checadas_en_turno_por_equipo"))

    # --- entradas y salidas: KPIs de rango en la corrida de 5 minutos ----------------------------------------

    def test_la_corrida_frecuente_recalcula_solo_hoy_en_entradas_y_salidas_y_no_pisa_otros_dias(self):
        ayer = D - timedelta(days=1)
        for clave in ("checadas_entradas_por_equipo", "checadas_salidas_por_equipo"):
            with transaction_context() as db:                # lo que ya estaba guardado de ayer (y que ya no cambia)
                db.add(KpiSnapshot(id_kpi_definition=self.ids[clave], dimension_key={"id_team": NORTE}, periodo=ayer, valor=Decimal("7")))
        self._checada(ANA, local(ayer, 9, 0), local(ayer, 17, 0))      # una checada de ayer: la corrida de 5 min no la mira
        self._checada(ANA, local(D, 9, 0), local(D, 12, 0))            # una de hoy, ya cerrada
        with self._con_registro(self.frecuentes), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        for clave in ("checadas_entradas_por_equipo", "checadas_salidas_por_equipo"):
            guardado = self._guardado(clave)
            self.assertEqual({ayer, D}, set(guardado), f"{clave}: no inventa ni toca otros dias")
            self.assertEqual({NORTE: 7.0}, guardado[ayer], f"{clave}: ayer sigue como estaba")
            self.assertEqual({NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}, guardado[D], clave)

    def test_cancelar_la_unica_entrada_del_dia_baja_el_conteo_a_cero_en_la_corrida_siguiente(self):
        # El cero explicito por equipo y dia: si la fila no saliera, el 1 de antes se quedaria pegado.
        id_checada = self._checada(ANA, local(D, 9, 0))
        with self._con_registro(self.frecuentes), ahora_local(local(D, 10, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual(1.0, self._guardado("checadas_entradas_por_equipo")[D][NORTE])
        with transaction_context() as db:
            db.get(Incident, id_checada).incident_status = "cancelada"
        with self._con_registro(self.frecuentes), ahora_local(local(D, 10, 5)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual(0.0, self._guardado("checadas_entradas_por_equipo")[D][NORTE])

    def test_la_nocturna_si_recalcula_los_siete_dias_de_entradas_y_salidas(self):
        antier = D - timedelta(days=2)
        self._checada(ANA, local(antier, 9, 0), local(antier, 17, 0))
        with self._con_registro(self.frecuentes), self._contenedor_con_fecha(D), ahora_local(local(D, 19, 0)):
            tasks_kpis.recalculate_kpi_snapshots()
        entradas = self._guardado("checadas_entradas_por_equipo")
        self.assertEqual(7, len(entradas), "los siete dias de la ventana, cada uno con sus ceros")
        self.assertEqual(1.0, entradas[antier][NORTE])
        self.assertEqual(0.0, entradas[D][NORTE])

    # --- la primera hora local: las cinco claves con (ayer, hoy) ----------------------------------------------

    def _llamadas_con_rango_a_las(self, hora_local):
        """`(rango de las cinco claves, rango de restaurante)` con el que la corrida de 5 minutos llamo a cada KPI a esa hora local."""
        espias = []
        for kpi in self.frecuentes:
            copia = copy.copy(kpi)
            copia.query_builder = mock.Mock(return_value=[])
            espias.append(copia)
        restaurante = copy.copy(KPI_POR_CLAVE["ventas_restaurante"])
        restaurante.query_builder = mock.Mock(return_value=[])
        with self._con_registro((*espias, restaurante)), ahora_local(hora_local):
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()

        def rangos(kpi):
            return {(llamada.args[1], llamada.args[2]) for llamada in kpi.query_builder.call_args_list}

        de_las_claves = set().union(*(rangos(kpi) for kpi in espias))
        for kpi in espias:
            self.assertTrue(kpi.query_builder.called, f"{kpi.clave} se llama siempre")
        return de_las_claves, rangos(restaurante), resultado

    def test_los_limites_de_la_primera_hora_en_la_corrida_real(self):
        casos = [
            (local(D, 23, 59), (D, D), "23:59"),
            (local(D1, 0, 0), (D, D1), "00:00"),
            (local(D1, 0, 59), (D, D1), "00:59"),
            (local(D1, 1, 0), (D1, D1), "01:00"),
        ]
        for hora, (inicio, fin), motivo in casos:
            with self.subTest(motivo):
                de_las_claves, de_restaurante, resultado = self._llamadas_con_rango_a_las(hora)
                self.assertEqual({(inicio, fin)}, de_las_claves, "las cinco claves, todas con el mismo rango")
                hoy = hora.date()
                self.assertEqual({(hoy, hoy)}, de_restaurante, "restaurante nunca incluye ayer")
                self.assertEqual(inicio.isoformat(), resultado["fecha_inicio_claves"])
                self.assertEqual((hoy.isoformat(), hoy.isoformat()), (resultado["fecha_inicio"], resultado["fecha_fin"]))

    def test_en_la_primera_hora_el_resto_de_operaciones_sigue_sin_correr(self):
        ajena = copy.copy(KPI_POR_CLAVE["incidencias_abiertas_por_empleado"])
        ajena.query_builder = mock.Mock(return_value=[])
        with self._con_registro((*self.frecuentes, ajena)), ahora_local(local(D1, 0, 30)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        ajena.query_builder.assert_not_called()

    def test_las_fotos_no_cambian_en_la_primera_hora(self):
        self._checada(ANA, local(D, 22, 0))                 # a las 00:30 lleva 2 h 30 min: en turno (Norte)
        self._checada(BETO, local(D, 11, 0))                # 13 h 30 min: sin salida (Norte y Sur); no es candidata del KPI por persona
        for clave in ("checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo"):
            with transaction_context() as db:               # lo que dejo ayer la corrida de 5 minutos: una foto de ayer no se reescribe
                db.add(KpiSnapshot(id_kpi_definition=self.ids[clave], dimension_key={"id_team": NORTE}, periodo=D, valor=Decimal("5")))
        with self._con_registro(self.frecuentes), ahora_local(local(D1, 0, 30)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        en_turno = self._guardado("checadas_en_turno_por_equipo")
        sin_salida = self._guardado("checadas_sin_salida_por_equipo")
        self.assertEqual({D, D1}, set(en_turno), "solo hoy; ayer es el que ya estaba")
        self.assertEqual({NORTE: 5.0}, en_turno[D])
        self.assertEqual({NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}, en_turno[D1])
        self.assertEqual({NORTE: 5.0}, sin_salida[D])
        self.assertEqual({NORTE: 1.0, SUR: 1.0, VACIO: 0.0, None: 0.0}, sin_salida[D1])
        self.assertEqual({D1: {ANA: 150.0}}, self._guardado("checadas_en_turno_por_empleado", "id_user"))

    def test_una_marca_de_ayer_capturada_a_las_0030_completa_sus_entradas_y_salidas(self):
        with self._con_registro(self.frecuentes), ahora_local(local(D, 23, 55)):         # la ultima corrida de ayer
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual({D: {NORTE: 0.0, SUR: 0.0, VACIO: 0.0, None: 0.0}}, self._guardado("checadas_entradas_por_equipo"))
        self._checada(ANA, local(D, 23, 58), local(D, 23, 59))      # una marca de ayer que n8n capturo despues de medianoche
        with self._con_registro(self.frecuentes), ahora_local(local(D1, 0, 30)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        for clave in ("checadas_entradas_por_equipo", "checadas_salidas_por_equipo"):
            guardado = self._guardado(clave)
            self.assertEqual({NORTE: 1.0, SUR: 0.0, VACIO: 0.0, None: 0.0}, guardado[D], f"{clave}: ayer se completa a las 00:30")
            self.assertEqual({NORTE: 0.0, SUR: 0.0, VACIO: 0.0, None: 0.0}, guardado[D1], f"{clave}: hoy, con sus ceros")

    def test_a_la_1_en_punto_una_marca_tardia_de_ayer_ya_no_se_refleja_en_la_corrida_de_5_minutos(self):
        with self._con_registro(self.frecuentes), ahora_local(local(D1, 0, 59)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self._checada(ANA, local(D, 23, 58), local(D, 23, 59))
        with self._con_registro(self.frecuentes), ahora_local(local(D1, 1, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual(D1.isoformat(), resultado["fecha_inicio_claves"])
        self.assertEqual(0.0, self._guardado("checadas_entradas_por_equipo")[D][NORTE], "esa la completa la corrida nocturna, no esta")

    # --- las anomalias son nocturnas -----------------------------------------------------------------------

    def test_las_anomalias_las_escribe_la_nocturna_por_dia_de_salida_y_la_corrida_de_5_minutos_no_las_toca(self):
        anomala = KPI_POR_CLAVE["checadas_con_duracion_anomala"]
        self._checada(ANA, local(D - timedelta(days=10), 8, 0), local(D, 9, 0))      # entrada de hace 10 dias, salida hoy
        with self._con_registro((*self.frecuentes, anomala)), ahora_local(local(D, 15, 0)):
            resultado = tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertNotIn("checadas_con_duracion_anomala", resultado["claves"])
        self.assertEqual({}, self._guardado("checadas_con_duracion_anomala", "id_user"), "la de 5 minutos no la calcula")
        with self._con_registro((*self.frecuentes, anomala)), self._contenedor_con_fecha(D), ahora_local(local(D, 19, 0)):
            tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual({D: {ANA: 1.0}}, self._guardado("checadas_con_duracion_anomala", "id_user"),
                         "la nocturna la ve el dia de la salida, aunque la entrada ya no este en su ventana de 7 dias")

    # --- la foto por persona -------------------------------------------------------------------------------

    def test_quien_sale_de_turno_queda_en_cero_en_la_corrida_siguiente(self):
        a = self._checada(ANA, local(D, 12, 0))
        self._checada(BETO, local(D, 13, 0))
        with self._con_registro(self.frecuentes), ahora_local(local(D, 15, 0)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        self.assertEqual({D: {ANA: 180.0, BETO: 120.0}}, self._guardado("checadas_en_turno_por_empleado", "id_user"))
        self._cerrar(a, local(D, 15, 10))
        with self._con_registro(self.frecuentes), ahora_local(local(D, 15, 30)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()
        # Ana no desaparece: su fila se pisa con 0 (la API la oculta), y Beto sigue sumando minutos.
        self.assertEqual({D: {ANA: 0.0, BETO: 150.0}}, self._guardado("checadas_en_turno_por_empleado", "id_user"))


class EquipoDadoDeBajaEnLosKpisTest(ChecadasBase):
    """Dar de baja un equipo POR LA API (no escribiendo `deletion_date` a mano): sus integrantes pasan a «Sin equipo»."""

    def _dar_de_baja_el_equipo(self, id_team):
        token = jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        respuesta = self.client.delete(f"/team/{id_team}", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, respuesta.status_code, respuesta.get_json())

    def _foto_de(self, consulta):
        return {id_team: valor for id_team, (_, valor) in self._foto(consulta, D).items()}

    def test_los_integrantes_pasan_a_sin_equipo_si_no_tienen_otro_equipo_vigente(self):
        self._checada(ANA, local(D, 10, 0))      # Norte (y el equipo que ya no existe)
        self._checada(BETO, local(D, 10, 0))     # Norte y Sur
        self._checada(CARLA, local(D, 10, 0))    # Sur
        with ahora_local(local(D, 15, 0)):
            antes = self._foto_de(checadas_en_turno_por_equipo_query)
        self.assertEqual({NORTE: 2, SUR: 2, VACIO: 0, None: 0}, antes)

        self._dar_de_baja_el_equipo(NORTE)

        with ahora_local(local(D, 15, 0)):
            despues = self._foto_de(checadas_en_turno_por_equipo_query)
        self.assertNotIn(NORTE, despues, "un equipo de baja ya no sale como equipo")
        self.assertEqual(2, despues[SUR], "Beto y Carla siguen en Sur")
        self.assertEqual(1, despues[None], "Ana se quedo sin ningun equipo vigente: «Sin equipo»")

    def test_quien_sale_de_un_equipo_por_la_api_y_no_tiene_otro_pasa_a_sin_equipo(self):
        self._checada(CARLA, local(D, 10, 0))    # Sur
        with transaction_context() as db:
            membresia = db.query(NmTeamUser).filter_by(id_team=SUR, id_user=CARLA).one().id_nm_team_user
        token = jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")

        respuesta = self.client.delete(f"/nm_team_user/{membresia}", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(200, respuesta.status_code)
        with ahora_local(local(D, 15, 0)):
            foto = self._foto_de(checadas_en_turno_por_equipo_query)
        self.assertEqual({NORTE: 0, SUR: 0, VACIO: 0, None: 1}, foto)


# Lunes a jueves de la semana de referencia: D es jueves 15 de octubre de 2026.
LUN, MAR, MIE, JUE = D - timedelta(days=3), D - timedelta(days=2), D - timedelta(days=1), D


class EquipoEnElMomentoDeLaMarcaTest(ChecadasBase):
    """Cada marca cuenta en el equipo que la persona tenia EN ESE MOMENTO, no en el de hoy.

    Diego no tiene equipo en el fixture: aqui se le arman membresias a la medida. Las fechas de las membresias se
    escriben en hora de pared y se guardan en UTC (como las guarda el sistema): la conversion es lo que se prueba.
    """

    def _membresia(self, id_team, desde_pared, hasta_pared=None, id_user=DIEGO):
        with transaction_context() as db:
            db.add(NmTeamUser(
                id_team=id_team, id_user=id_user, created_by=1, creation_date=pared_a_utc(desde_pared),
                deletion_date=None if hasta_pared is None else pared_a_utc(hasta_pared),
            ))

    def _entradas(self, inicio=LUN, fin=JUE):
        """`{(id_team, dia): entradas}` de los equipos, sin los ceros; y `{dia: entradas}` de «Sin equipo»."""
        filas = self._marcas(checadas_entradas_por_equipo_query, inicio, fin)
        equipos = {(id_team, dia): n for id_team, dia, n in filas if id_team is not None and n}
        sin_equipo = {dia: n for id_team, dia, n in filas if id_team is None and n}
        return equipos, sin_equipo

    def _salidas(self, inicio=LUN, fin=JUE):
        filas = self._marcas(checadas_salidas_por_equipo_query, inicio, fin)
        equipos = {(id_team, dia): n for id_team, dia, n in filas if id_team is not None and n}
        sin_equipo = {dia: n for id_team, dia, n in filas if id_team is None and n}
        return equipos, sin_equipo

    # --- pasar de un equipo a otro --------------------------------------------------------------------------

    def test_quien_pasa_de_a_a_b_el_miercoles_conserva_el_lunes_y_el_martes_en_a(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MIE, 9, 0))
        self._membresia(SUR, local(MIE, 9, 0))
        for dia, hora in ((LUN, 10), (MAR, 15), (MIE, 8), (MIE, 10), (JUE, 10)):
            self._checada(DIEGO, local(dia, hora, 0))

        equipos, sin_equipo = self._entradas()

        self.assertEqual(
            {(NORTE, LUN): 1, (NORTE, MAR): 1, (NORTE, MIE): 1, (SUR, MIE): 1, (SUR, JUE): 1}, equipos,
            "lunes, martes y el miercoles antes de las 9:00 son de Norte; desde las 9:00 del miercoles, de Sur",
        )
        self.assertEqual({}, sin_equipo)

    def test_el_equipo_de_hoy_no_reescribe_el_pasado(self):
        # Hoy Diego esta en Sur; sus marcas de la semana pasada siguen siendo de Norte.
        self._membresia(NORTE, local(LUN, 0, 0), local(JUE, 0, 0))
        self._membresia(SUR, local(JUE, 0, 0))
        self._checada(DIEGO, local(LUN, 10, 0))

        with ahora_local(local(JUE, 15, 0)):
            equipos, _ = self._entradas()

        self.assertEqual({(NORTE, LUN): 1}, equipos)

    def test_de_a_a_b_y_de_vuelta_a_a_atribuye_cada_marca_a_su_periodo(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MAR, 12, 0))
        self._membresia(SUR, local(MAR, 12, 0), local(MIE, 12, 0))
        self._membresia(NORTE, local(MIE, 12, 0))
        for dia, hora in ((MAR, 10), (MAR, 14), (MIE, 10), (MIE, 14)):
            self._checada(DIEGO, local(dia, hora, 0))

        equipos, _ = self._entradas()

        self.assertEqual({(NORTE, MAR): 1, (SUR, MAR): 1, (SUR, MIE): 1, (NORTE, MIE): 1}, equipos)

    def test_la_salida_va_al_equipo_que_la_persona_tenia_al_marcar_la_salida(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MIE, 12, 0))
        self._membresia(SUR, local(MIE, 12, 0))
        self._checada(DIEGO, local(MIE, 8, 0), local(MIE, 17, 0))     # entra en Norte, sale en Sur

        entradas, _ = self._entradas()
        salidas, _ = self._salidas()

        self.assertEqual({(NORTE, MIE): 1}, entradas)
        self.assertEqual({(SUR, MIE): 1}, salidas)

    # --- los bordes del intervalo y de la zona -------------------------------------------------------------

    def test_la_membresia_cubre_desde_su_alta_hasta_su_baja_y_el_instante_exacto_de_la_baja_ya_es_del_siguiente(self):
        self._membresia(NORTE, local(MIE, 9, 0), local(MIE, 12, 0))
        self._membresia(SUR, local(MIE, 12, 0))
        self._checada(DIEGO, local(MIE, 8, 59, 59))     # un segundo antes del alta: sin equipo
        self._checada(DIEGO, local(MIE, 9, 0, 0))       # el instante exacto del alta: ya esta en Norte
        self._checada(DIEGO, local(MIE, 11, 59, 59))    # un segundo antes de la baja: Norte
        self._checada(DIEGO, local(MIE, 12, 0, 0))      # el instante exacto de la baja: ya es de Sur

        equipos, sin_equipo = self._entradas()

        self.assertEqual({(NORTE, MIE): 2, (SUR, MIE): 1}, equipos)
        self.assertEqual({MIE: 1}, sin_equipo)

    def test_cruce_de_medianoche_local(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MAR, 23, 59, 59))
        self._membresia(SUR, local(MAR, 23, 59, 59))
        self._checada(DIEGO, local(MAR, 23, 59, 58))
        self._checada(DIEGO, local(MIE, 0, 0, 1))

        equipos, _ = self._entradas()

        self.assertEqual({(NORTE, MAR): 1, (SUR, MIE): 1}, equipos)

    def test_cruce_de_medianoche_utc_las_18_horas_de_mexico(self):
        # Sur empieza a las 19:00 locales del miercoles = 01:00 UTC del jueves. Una marca de las 20:00 locales (02:00 UTC del
        # jueves) ya es de Sur; sin convertir la zona se compararia "miercoles 20:00" contra "jueves 01:00" y saldria de Norte.
        self._membresia(NORTE, local(LUN, 0, 0), local(MIE, 19, 0))
        self._membresia(SUR, local(MIE, 19, 0))
        self._checada(DIEGO, local(MIE, 18, 30))
        self._checada(DIEGO, local(MIE, 20, 0))

        equipos, _ = self._entradas()

        self.assertEqual({(NORTE, MIE): 1, (SUR, MIE): 1}, equipos)

    def test_las_checadas_de_noche_en_hora_utc_del_dia_siguiente_se_comparan_por_el_instante_real(self):
        # 23:50 de Mexico del martes ya es miercoles 05:50 UTC. Norte se dio de baja el martes a las 23:00 locales (05:00 UTC).
        self._membresia(NORTE, local(LUN, 0, 0), local(MAR, 23, 0))
        self._checada(DIEGO, local(MAR, 22, 59))
        self._checada(DIEGO, local(MAR, 23, 50))

        equipos, sin_equipo = self._entradas()

        self.assertEqual({(NORTE, MAR): 1}, equipos)
        self.assertEqual({MAR: 1}, sin_equipo)

    # --- sin equipo y varios equipos -----------------------------------------------------------------------

    def test_una_membresia_creada_despues_de_la_marca_no_cuenta(self):
        self._membresia(SUR, local(JUE, 12, 0))
        self._checada(DIEGO, local(JUE, 10, 0))
        self._checada(DIEGO, local(JUE, 13, 0))

        equipos, sin_equipo = self._entradas()

        self.assertEqual({(SUR, JUE): 1}, equipos, "solo la de las 13:00")
        self.assertEqual({JUE: 1}, sin_equipo, "la de las 10:00 es de cuando todavia no tenia equipo")

    def test_quien_nunca_tuvo_equipo_cuenta_en_sin_equipo(self):
        self._checada(DIEGO, local(MAR, 10, 0))
        self._checada(DIEGO, local(MIE, 10, 0))

        equipos, sin_equipo = self._entradas()

        self.assertEqual({}, equipos)
        self.assertEqual({MAR: 1, MIE: 1}, sin_equipo)

    def test_en_dos_equipos_a_la_vez_la_marca_cuenta_en_cada_uno(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MIE, 9, 0))
        self._membresia(SUR, local(MAR, 0, 0))                      # entre el martes y el miercoles esta en los dos
        self._checada(DIEGO, local(LUN, 10, 0))
        self._checada(DIEGO, local(MAR, 10, 0))
        self._checada(DIEGO, local(MIE, 10, 0))

        equipos, sin_equipo = self._entradas()

        self.assertEqual({(NORTE, LUN): 1, (NORTE, MAR): 1, (SUR, MAR): 1, (SUR, MIE): 1}, equipos)
        self.assertEqual({}, sin_equipo, "quien tiene equipo en ese momento nunca cuenta en «Sin equipo»")

    def test_quien_esta_en_un_equipo_dado_de_baja_y_en_otro_vigente_no_sale_en_sin_equipo(self):
        # Ana (fixture) esta en Norte y en el equipo que ya no existe.
        self._checada(ANA, local(MAR, 10, 0))

        equipos, sin_equipo = self._entradas()

        self.assertEqual({(NORTE, MAR): 1}, equipos)
        self.assertEqual({}, sin_equipo)

    # --- un equipo dado de baja a media semana ---------------------------------------------------------------

    def test_un_equipo_dado_de_baja_a_media_semana_conserva_los_dias_en_que_existio(self):
        with transaction_context() as db:
            db.add(Team(id_team=7010, team_description="Parque temporal", created_by=1, deletion_date=pared_a_utc(local(MIE, 12, 0))))
        self._membresia(7010, local(LUN, 0, 0), local(MIE, 12, 0))
        for dia, hora in ((LUN, 10), (MAR, 10), (MIE, 10), (MIE, 13), (JUE, 10)):
            self._checada(DIEGO, local(dia, hora, 0))

        with transaction_context() as db:
            filas = checadas_entradas_por_equipo_query(db, LUN, JUE, {}, None)

        del_equipo = {dia: n for id_team, dia, n in filas if id_team == 7010}
        self.assertEqual({LUN: 1, MAR: 1, MIE: 1}, del_equipo, "tiene fila (con su cero o su cuenta) solo hasta el dia de su baja")
        self.assertEqual({MIE: 1, JUE: 1}, {dia: n for id_team, dia, n in filas if id_team is None and n},
                         "despues de la baja, Diego queda sin equipo")

    def test_un_equipo_dado_de_baja_antes_del_rango_no_aparece(self):
        with transaction_context() as db:
            filas = checadas_entradas_por_equipo_query(db, LUN, JUE, {}, None)

        self.assertNotIn(BAJA, {id_team for id_team, _, _ in filas}, "el equipo cerrado en enero no tiene nada que ver con octubre")

    # --- las fotos de AHORA usan el equipo vigente hoy ------------------------------------------------------------

    def test_la_foto_de_ahora_usa_el_equipo_vigente_hoy(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MIE, 9, 0))
        self._membresia(SUR, local(MIE, 9, 0))
        self._checada(DIEGO, local(JUE, 10, 0))

        with ahora_local(local(JUE, 15, 0)):
            foto = {id_team: valor for id_team, (_, valor) in self._foto(checadas_en_turno_por_equipo_query, JUE).items()}

        # Diego suma a Sur, su equipo de hoy, y no a Norte, el de la semana pasada; nadie mas tiene checada abierta.
        self.assertEqual({NORTE: 0, SUR: 1, VACIO: 0, None: 0}, foto)

    # --- el ayudante: los equipos de una persona en un instante ------------------------------------------------

    def test_equipos_de_la_persona_en_un_instante(self):
        self._membresia(NORTE, local(MAR, 0, 0), local(MIE, 9, 0))
        self._membresia(SUR, local(MIE, 9, 0))
        self._membresia(VACIO, local(MIE, 9, 0), local(MIE, 18, 0))

        with transaction_context() as db:
            en = lambda pared: equipos_de_la_persona_en(db, DIEGO, pared)    # noqa: E731
            self.assertEqual((), en(local(LUN, 23, 59, 59)), "antes de su primer equipo")
            self.assertEqual((NORTE,), en(local(MAR, 0, 0)), "el instante exacto del alta ya cuenta")
            self.assertEqual((NORTE,), en(local(MIE, 8, 59, 59)))
            self.assertEqual((SUR, VACIO), en(local(MIE, 9, 0)), "el instante exacto de la baja ya no es del equipo; en dos equipos, los dos")
            self.assertEqual((SUR,), en(local(MIE, 18, 0)), "Vacio termina a las 18:00")
            self.assertEqual((SUR,), en(local(JUE, 10, 0)))

    def test_el_ayudante_convierte_la_hora_de_pared_a_utc_antes_de_comparar(self):
        # Sur empieza a las 19:00 locales = 01:00 UTC del dia siguiente.
        self._membresia(SUR, local(MIE, 19, 0))

        with transaction_context() as db:
            self.assertEqual((), equipos_de_la_persona_en(db, DIEGO, local(MIE, 18, 59)))
            self.assertEqual((SUR,), equipos_de_la_persona_en(db, DIEGO, local(MIE, 20, 0)))

    def test_el_ayudante_coincide_con_lo_que_cuentan_los_kpis(self):
        self._membresia(NORTE, local(LUN, 0, 0), local(MAR, 15, 0))
        self._membresia(SUR, local(MAR, 15, 0))
        marcas = [local(LUN, 10, 0), local(MAR, 14, 59), local(MAR, 15, 0), local(MIE, 10, 0)]
        for marca in marcas:
            self._checada(DIEGO, marca)

        equipos, _ = self._entradas()

        with transaction_context() as db:
            esperado = defaultdict(int)
            for marca in marcas:
                for id_team in equipos_de_la_persona_en(db, DIEGO, marca):
                    esperado[(id_team, marca.date())] += 1
        self.assertEqual(dict(esperado), equipos)

    # --- el dia completo (snapshots por persona) es la misma regla, evaluada al terminar el dia ---------------------

    def test_persona_en_equipos_el_dia_coincide_con_la_regla_por_instante_al_terminar_el_dia(self):
        casos = []
        altas = (local(MAR, 23, 59, 59), local(MIE, 0, 0, 0), local(MIE, 12, 0, 0))
        bajas = (None, local(MIE, 23, 59, 59), local(JUE, 0, 0, 0), local(JUE, 0, 0, 1))
        for alta in altas:
            for baja in bajas:
                casos.append((alta, baja))
        for alta, baja in casos:
            with self.subTest(alta=alta, baja=baja):
                with transaction_context() as db:
                    db.query(NmTeamUser).filter(NmTeamUser.id_user == DIEGO).delete()
                self._membresia(SUR, alta, baja)
                with transaction_context() as db:
                    for dia in (MAR, MIE, JUE):
                        fin_del_dia = datetime.combine(dia + timedelta(days=1), time.min) - timedelta(microseconds=1)
                        por_instante = SUR in equipos_de_la_persona_en(db, DIEGO, fin_del_dia)
                        por_dia = db.scalar(select(persona_en_equipos_el_dia(literal(DIEGO), [SUR], literal(dia, Date))))
                        self.assertEqual(por_instante, bool(por_dia), f"dia {dia}")

