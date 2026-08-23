from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from app.models.appointment import AppointmentType, AvailabilityRule, CalendarProfile
from app.models.session import transaction_context
from app.services.appointment_service import create_appointment_type
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestAppointmentsApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        now = datetime.now(timezone.utc)
        self.booking_start = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        with transaction_context() as db:
            profile = CalendarProfile(id_user=1, id_proyect=1, calendar_code="demo", display_name="Demo", timezone="UTC", created_by=1)
            db.add(profile)
            db.flush()
            self.profile_id = profile.id_calendar_profile
            appointment_type = AppointmentType(
                id_calendar_profile=profile.id_calendar_profile,
                name="Consulta",
                duration_minutes=30,
                booking_horizon_days=30,
                created_by=1,
            )
            db.add(appointment_type)
            db.flush()
            db.add(AvailabilityRule(
                id_calendar_profile=profile.id_calendar_profile,
                weekday=self.booking_start.weekday(),
                start_time=time(9, 0),
                end_time=time(12, 0),
                created_by=1,
            ))
            self.type_id = appointment_type.id_appointment_type

    def test_unconfigured_meeting_provider_is_rejected(self):
        with self.assertRaises(AppError) as context:
            create_appointment_type(self.profile_id, {
                "name": "Videollamada",
                "duration_minutes": 30,
                "meeting_provider": "google",
            }, {"id_user": 1, "id_proyect": 1})
        self.assertEqual(context.exception.status_code, 501)
        self.assertEqual(context.exception.message_key, "errors.calendar_provider_not_configured")

    def test_public_booking_rejects_a_second_booking_for_the_same_slot(self):
        payload = {
            "id_appointment_type": self.type_id,
            "starts_at": self.booking_start.isoformat(),
            "timezone": "UTC",
            "guest_name": "Ada Lovelace",
            "guest_email": "ada@example.com",
        }
        first = self.client.post("/public/calendars/demo/appointments", json=payload)
        second = self.client.post("/public/calendars/demo/appointments", json=payload)

        self.assertEqual(first.status_code, 201)
        first_payload = self.json(first)
        self.assertIn("management_token", first_payload)
        self.assertNotIn("management_token_hash", first_payload)
        self.assertNotIn("id_proyect", first_payload)
        self.assertNotIn("created_by", first_payload)
        self.assertNotIn("guest_email", first_payload)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.json(second)["error_key"], "errors.appointment_slot_unavailable")

        cancelled = self.client.post(f"/public/appointments/{first_payload['management_token']}/cancel")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(self.json(cancelled)["status"], "cancelled")

        available_again = self.client.post("/public/calendars/demo/appointments", json=payload)
        self.assertEqual(available_again.status_code, 201)