"""La convencion de fechas: auditoria en UTC con `Z`, negocio en hora de pared.

El sintoma que origino esto: en la tabla de incidencias, `creation_date` salia
a las 8:33 p.m. cuando eran las 2:33 p.m. La base guarda UTC, la API la entregaba
sin zona y la pantalla la tomaba por hora local.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest import TestCase

from app.models import Brand
from app.services.incident_service import IncidentService, _as_datetime
from app.utils.tiempo import ZONA_NEGOCIO, a_iso_utc, ahora_negocio, ahora_utc
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
