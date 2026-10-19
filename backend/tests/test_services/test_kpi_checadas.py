"""KPIs de checadas (entrada/salida) de Comala: filas de `incident` con coordenadas.

Corren en SQLite y en PostgreSQL (solo usan SQL portable). `incident_date` y `close_date` son hora de pared
del negocio, sin zona; "ahora" sale de `ahora_negocio()`, que aqui se congela en un instante UTC concreto y
deja que el codigo real haga la conversion a hora de Mexico (UTC-6 todo el ano desde 2022).
"""

from __future__ import annotations

import inspect
import unittest
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import text

from app.kpis.modulos import checadas
from app.kpis.modulos.checadas import (
    UMBRAL_SIN_SALIDA_HORAS,
    checadas_en_turno_por_equipo_query,
    checadas_entradas_por_equipo_query,
    checadas_salidas_por_equipo_query,
    checadas_sin_salida_por_equipo_query,
)
from app.kpis.registry import KPI_POR_CLAVE
from app.models import (
    CustomerSupplier, Department, Incident, IncidentType, Level, NmTeamUser, Permission, Proyect, Status,
    Subdepartment, Team, User,
)
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase

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


@contextmanager
def reloj_en_utc(instante_utc: datetime):
    """Congela `datetime.now(...)` de `app.utils.tiempo` en un instante UTC.

    `ahora_negocio()` sigue convirtiendo con `ZONA_NEGOCIO`: lo que se prueba es esa conversion real, no una
    hora local escrita a mano.
    """
    fijo = instante_utc.replace(tzinfo=timezone.utc)

    class _Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return fijo.astimezone(tz) if tz else fijo.replace(tzinfo=None)

    with patch("app.utils.tiempo.datetime", _Reloj):
        yield


def ahora_local(hora_local: datetime):
    """El mismo reloj, dado en hora de Mexico (UTC-6): las 15:00 locales son las 21:00 UTC."""
    return reloj_en_utc(hora_local + timedelta(hours=6))


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


class DefinicionesDeFlujosTest(unittest.TestCase):
    def test_entradas_y_salidas_son_flujos_por_equipo_de_operaciones_y_solo_barras(self):
        for clave in ("checadas_entradas_por_equipo", "checadas_salidas_por_equipo"):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, clave)
            self.assertEqual(("equipo",), kpi.dimensiones, clave)
            self.assertEqual("suma", kpi.agregacion, clave)
            self.assertEqual("snapshot", kpi.modo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertEqual(("barras",), tuple(kpi.graficas_permitidas), clave)


class DefinicionesDeChecadasTest(unittest.TestCase):
    CLAVES_DE_FOTO = ("checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo")

    def test_el_criterio_de_checada_vive_en_un_solo_lugar(self):
        # `es_checada()` es la unica que nombra `Incident.latitude`; las consultas la reutilizan.
        fuente = inspect.getsource(checadas)
        self.assertEqual(1, fuente.count("Incident.latitude"), "el criterio no se repite en cada consulta")
        self.assertIn("es_checada()", inspect.getsource(checadas.checadas_vigentes))

    def test_los_kpis_de_foto_son_de_operaciones_por_equipo_y_solo_barras(self):
        for clave in self.CLAVES_DE_FOTO:
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, clave)
            self.assertEqual(("equipo",), kpi.dimensiones, clave)
            self.assertEqual("ultimo", kpi.agregacion, clave)
            self.assertEqual("snapshot", kpi.modo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            # Una persona en dos equipos cuenta en cada uno: el total entre equipos la contaria dos veces. Solo
            # barras (un valor por equipo); "numero" y "linea" usan ese total.
            self.assertEqual(("barras",), tuple(kpi.graficas_permitidas), clave)
            self.assertEqual("barras", kpi.grafica_default, clave)

    def test_sin_salida_es_mejor_cuando_baja(self):
        self.assertEqual("bajo_es_mejor", KPI_POR_CLAVE["checadas_sin_salida_por_equipo"].direccion)
        self.assertEqual("neutral", KPI_POR_CLAVE["checadas_en_turno_por_equipo"].direccion)
