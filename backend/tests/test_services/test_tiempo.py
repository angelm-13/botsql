"""La convencion de fechas: auditoria en UTC con `Z`, negocio en hora de pared.

El sintoma que origino esto: en la tabla de incidencias, `creation_date` salia
a las 8:33 p.m. cuando eran las 2:33 p.m. La base guarda UTC, la API la entregaba
sin zona y la pantalla la tomaba por hora local.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest import TestCase

from sqlalchemy import DateTime, literal, select

from app.models import Brand
from app.models.session import transaction_context
from app.services.incident_service import IncidentService, _as_datetime
from app.utils.tiempo import (
    ZONA_NEGOCIO, a_iso_utc, ahora_negocio, ahora_utc, hora_pared_a_utc, pared_a_utc, utc_a_pared,
)
from tests.conftest import BackendTestCase
from tests.test_services.test_operations_workflow import OperationsTestCase


class TestAIsoUtc(TestCase):
    def test_a_naive_date_is_taken_as_utc_and_marked_with_z(self):
        self.assertEqual("2026-10-14T20:33:16.049979Z", a_iso_utc(datetime(2026, 10, 14, 20, 33, 16, 49979)))

    def test_an_aware_date_is_converted_to_utc(self):
        menos_seis = timezone(timedelta(hours=-6))
        self.assertEqual("2026-10-14T20:33:00Z", a_iso_utc(datetime(2026, 10, 14, 14, 33, tzinfo=menos_seis)))

    def test_none_stays_none_and_a_plain_date_has_no_zone(self):
        self.assertIsNone(a_iso_utc(None))
        self.assertEqual("2026-10-14", a_iso_utc(date(2026, 10, 14)))


class TestParedAUtc(TestCase):
    """`incident_date` es hora de pared (GMT-6); `creation_date`/`deletion_date` son UTC. Comparar sin convertir se equivoca 6 h."""

    def test_las_20_horas_de_mexico_son_las_2_de_la_madrugada_del_dia_siguiente_en_utc(self):
        self.assertEqual(datetime(2026, 10, 16, 2, 0), pared_a_utc(datetime(2026, 10, 15, 20, 0)))

    def test_conserva_los_microsegundos(self):
        self.assertEqual(datetime(2026, 10, 16, 2, 0, 0, 123456), pared_a_utc(datetime(2026, 10, 15, 20, 0, 0, 123456)))

    def test_el_borde_de_las_18_horas_locales_es_la_medianoche_utc(self):
        self.assertEqual(datetime(2026, 10, 15, 23, 59, 59), pared_a_utc(datetime(2026, 10, 15, 17, 59, 59)))
        self.assertEqual(datetime(2026, 10, 16, 0, 0, 0), pared_a_utc(datetime(2026, 10, 15, 18, 0, 0)))

    def test_ida_y_vuelta(self):
        pared = datetime(2026, 10, 15, 23, 50, 7, 5)
        self.assertEqual(pared, utc_a_pared(pared_a_utc(pared)))

    def test_una_fecha_con_zona_se_convierte_a_utc_tal_cual(self):
        menos_seis = timezone(timedelta(hours=-6))
        self.assertEqual(datetime(2026, 10, 16, 2, 0), pared_a_utc(datetime(2026, 10, 15, 20, 0, tzinfo=menos_seis)))


class TestHoraParedAUtcEnSql(BackendTestCase):
    """La misma conversion, escrita en SQL para compararla dentro de una consulta (en PostgreSQL se prueba con las checadas)."""

    def _en_sql(self, pared):
        with transaction_context() as db:
            return db.scalar(select(hora_pared_a_utc(literal(pared, DateTime))))

    def test_coincide_con_la_conversion_de_python(self):
        for pared in (
            datetime(2026, 10, 15, 20, 0), datetime(2026, 10, 15, 17, 59, 59), datetime(2026, 10, 15, 18, 0, 0),
            datetime(2026, 10, 15, 23, 59, 59), datetime(2026, 12, 31, 20, 30), datetime(2026, 10, 15, 20, 0, 0, 123456),
        ):
            self.assertEqual(pared_a_utc(pared), self._en_sql(pared), pared)


class TestRelojDelNegocio(TestCase):
    def test_business_time_is_six_hours_behind_utc(self):
        # Mexico no tiene horario de verano desde 2022: el desfase es fijo.
        desfase = ahora_utc() - ahora_negocio()
        self.assertAlmostEqual(6 * 3600, desfase.total_seconds(), delta=5)
        self.assertEqual(timedelta(hours=-6), ZONA_NEGOCIO.utcoffset(datetime(2026, 10, 14, 12)))


class TestFechaDeNegocioConZona(TestCase):
    def test_a_naive_business_date_is_kept_as_written(self):
        self.assertEqual(datetime(2026, 10, 14, 14, 33, 12), _as_datetime("2026-10-14T14:33:12", "incident_date"))

    def test_a_date_with_offset_becomes_business_wall_time(self):
        self.assertEqual(datetime(2026, 10, 14, 14, 33), _as_datetime("2026-10-14T14:33:00-06:00", "incident_date"))

    def test_a_utc_date_becomes_business_wall_time(self):
        # Antes se le quitaba la `Z` sin convertir: las 20:33 UTC quedaban como 20:33 locales.
        self.assertEqual(datetime(2026, 10, 14, 14, 33), _as_datetime("2026-10-14T20:33:00Z", "incident_date"))


class TestFechasEnLaApi(OperationsTestCase):
    def _crear(self, **extra):
        return IncidentService.create({
            'incident_status': 'abierta', 'id_incident_type': 1, 'id_user': 7, 'created_by': 1, **extra,
        })

    def test_the_audit_dates_come_out_with_z(self):
        creada = self._crear(incident_date='2026-01-15T12:00:00')
        self.assertTrue(creada['creation_date'].endswith('Z'), creada['creation_date'])
        self.assertTrue(creada['last_update_date'].endswith('Z'), creada['last_update_date'])

    def test_the_business_date_comes_out_as_written_without_zone(self):
        creada = self._crear(incident_date='2026-01-15T12:00:00')
        self.assertEqual('2026-01-15T12:00:00', creada['incident_date'])

    def test_a_utc_incident_date_is_stored_as_business_wall_time(self):
        creada = self._crear(incident_date='2026-01-15T18:00:00Z')
        self.assertEqual('2026-01-15T12:00:00', creada['incident_date'])

    def test_a_date_six_hours_ahead_is_now_rejected_as_future(self):
        # Contra la hora UTC esto pasaba: 5 h adelante en hora de negocio es 1 h "pasada" en UTC.
        futura = (ahora_negocio() + timedelta(hours=5)).replace(microsecond=0).isoformat()
        from app.utils.errors import AppError
        with self.assertRaises(AppError) as contexto:
            self._crear(incident_date=futura)
        self.assertEqual('errors.incident_date_in_the_future', contexto.exception.message_key)

    def test_a_model_without_custom_serializer_also_marks_its_audit_dates(self):
        marca = Brand(brand_description='x', created_by=1, creation_date=datetime(2026, 10, 14, 20, 33))
        self.assertEqual('2026-10-14T20:33:00Z', marca.serialize()['creation_date'])
        self.assertIsNone(marca.serialize()['deletion_date'])


class TestDiaLocalEnSql(TestCase):
    """`dia_local` agrupa por el dia del negocio, no por el de UTC (en SQLite aqui; en Postgres, en test_kpi_restaurante)."""

    def _dia(self, momento):
        from sqlalchemy import create_engine, literal, select

        from app.utils.tiempo import dia_local

        with create_engine("sqlite://").connect() as con:
            return con.execute(select(dia_local(literal(momento.strftime("%Y-%m-%d %H:%M:%S"))))).scalar()

    def test_a_sale_at_18_10_local_stays_on_the_same_local_day(self):
        self.assertEqual(date(2026, 9, 15), self._dia(datetime(2026, 9, 16, 0, 10)))

    def test_23_50_and_00_10_local_fall_on_different_days(self):
        self.assertEqual(date(2026, 9, 15), self._dia(datetime(2026, 9, 16, 5, 50)))
        self.assertEqual(date(2026, 9, 16), self._dia(datetime(2026, 9, 16, 6, 10)))

    def test_hoy_negocio_is_the_business_date_not_the_container_date(self):
        from app.utils.tiempo import hoy_negocio

        self.assertEqual(ahora_negocio().date(), hoy_negocio())
