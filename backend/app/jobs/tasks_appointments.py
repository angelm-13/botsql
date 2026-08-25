from __future__ import annotations

import smtplib
from datetime import UTC, datetime, timedelta

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.models.appointment import Appointment, AppointmentType, CalendarProfile
from app.models.session import transaction_context
from app.services.email_service import email_configured, send_email


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _appointment_email(record: Appointment, appointment_type: AppointmentType, profile: CalendarProfile, *, reminder: bool) -> tuple[str, str]:
    starts_at = record.starts_at.strftime("%Y-%m-%d %H:%M UTC")
    subject = f"Recordatorio: {appointment_type.name}" if reminder else f"Cita confirmada: {appointment_type.name}"
    prefix = "Te recordamos tu cita" if reminder else "Tu cita fue confirmada"
    lines = [prefix, "", f"Agenda: {profile.display_name}", f"Fecha: {starts_at}", f"Zona horaria seleccionada: {record.guest_timezone}"]
    if record.meeting_url:
        lines.extend(["", f"Enlace: {record.meeting_url}"])
    return subject, "\n".join(lines)


@celery.task(
    bind=True,
    name="app.jobs.tasks_appointments.send_appointment_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_appointment_email(self, appointment_id: int, reminder: bool = False) -> dict:
    del self
    with transaction_context() as db:
        record = db.query(Appointment).filter(Appointment.id_appointment == appointment_id).with_for_update().first()
        if not record or record.status != "confirmed":
            return result_ok("jobs.appointments.skipped", appointment_id=appointment_id)
        timestamp_field = "reminder_sent_at" if reminder else "confirmation_sent_at"
        if getattr(record, timestamp_field):
            return result_ok("jobs.appointments.already_sent", appointment_id=appointment_id)
        appointment_type = db.get(AppointmentType, record.id_appointment_type)
        profile = db.get(CalendarProfile, record.id_calendar_profile)
        subject, text = _appointment_email(record, appointment_type, profile, reminder=reminder)
        if not send_email(record.guest_email, subject, text):
            return result_ok("jobs.appointments.smtp_not_configured", appointment_id=appointment_id)
        setattr(record, timestamp_field, _now_naive())
        return result_ok("jobs.appointments.email_sent", appointment_id=appointment_id, reminder=reminder)


@celery.task(name="app.jobs.tasks_appointments.dispatch_due_notifications")
def dispatch_due_notifications() -> dict:
    if not email_configured():
        return result_ok("jobs.appointments.smtp_not_configured")
    now = _now_naive()
    with transaction_context() as db:
        confirmation_ids = [row[0] for row in db.query(Appointment.id_appointment).filter(
            Appointment.status == "confirmed",
            Appointment.confirmation_sent_at.is_(None),
            Appointment.creation_date >= now - timedelta(days=7),
        ).limit(500).all()]
        reminder_ids = [row[0] for row in db.query(Appointment.id_appointment).filter(
            Appointment.status == "confirmed",
            Appointment.reminder_sent_at.is_(None),
            Appointment.starts_at >= now + timedelta(hours=23, minutes=55),
            Appointment.starts_at <= now + timedelta(hours=24, minutes=5),
        ).limit(500).all()]
    for appointment_id in confirmation_ids:
        send_appointment_email.delay(appointment_id, False)
    for appointment_id in reminder_ids:
        send_appointment_email.delay(appointment_id, True)
    return result_ok("jobs.appointments.notifications_dispatched", confirmations=len(confirmation_ids), reminders=len(reminder_ids))