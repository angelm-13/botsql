from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from app.models.appointment import Appointment, AppointmentType, AvailabilityOverride, AvailabilityRule, CalendarProfile
from app.models.session import transaction_context
from app.utils.errors import AppError


ACTIVE_STATUSES = ("pending_confirmation", "confirmed")


def _public_type_payload(record: AppointmentType) -> dict:
    return {
        "id_appointment_type": record.id_appointment_type,
        "name": record.name,
        "description": record.description,
        "duration_minutes": record.duration_minutes,
        "meeting_provider": record.meeting_provider,
    }


def _public_appointment_payload(record: Appointment) -> dict:
    return {
        "id_appointment": record.id_appointment,
        "id_appointment_type": record.id_appointment_type,
        "guest_name": record.guest_name,
        "starts_at": record.starts_at.isoformat(),
        "ends_at": record.ends_at.isoformat(),
        "guest_timezone": record.guest_timezone,
        "status": record.status,
        "meeting_provider": record.meeting_provider,
        "meeting_url": record.meeting_url,
        "external_status": record.external_status,
    }


def _integer(value, field: str, *, minimum=0, maximum=None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if result < minimum or (maximum is not None and result > maximum):
        raise AppError("errors.invalid_field", 400, {"field": field})
    return result


def _zone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(value or "UTC"))
    except ZoneInfoNotFoundError as exc:
        raise AppError("errors.invalid_field", 400, {"field": "timezone"}) from exc


def _parse_date(value, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _parse_time(value, field: str) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _parse_datetime(value, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if parsed.tzinfo is None:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return parsed.astimezone(timezone.utc)


def _actor(user_data: dict) -> tuple[int, int]:
    try:
        return int(user_data.get("id_user") or user_data.get("user_id")), int(user_data.get("id_proyect") or user_data.get("project_id"))
    except (TypeError, ValueError) as exc:
        raise AppError("errors.auth_required", 401) from exc


def _profile_for_actor(db, profile_id, user_data: dict) -> CalendarProfile:
    actor_id, project_id = _actor(user_data)
    profile = (
        db.query(CalendarProfile)
        .filter(CalendarProfile.id_calendar_profile == _integer(profile_id, "id_calendar_profile", minimum=1))
        .filter(CalendarProfile.id_user == actor_id, CalendarProfile.id_proyect == project_id)
        .filter(CalendarProfile.deletion_date.is_(None))
        .first()
    )
    if not profile:
        raise AppError("errors.resource_not_found", 404)
    return profile


def create_profile(payload: dict, user_data: dict) -> dict:
    actor_id, project_id = _actor(user_data)
    code = re.sub(r"[^a-z0-9-]", "-", str(payload.get("calendar_code") or "").strip().lower()).strip("-")
    if not code or not payload.get("display_name"):
        raise AppError("errors.invalid_field", 400, {"field": "calendar_code" if not code else "display_name"})
    zone_name = str(payload.get("timezone") or "UTC")
    _zone(zone_name)
    with transaction_context() as db:
        if db.query(CalendarProfile).filter(CalendarProfile.calendar_code == code).first():
            raise AppError("errors.calendar_code_conflict", 409)
        profile = CalendarProfile(
            id_user=actor_id,
            id_proyect=project_id,
            calendar_code=code,
            display_name=str(payload["display_name"]).strip(),
            timezone=zone_name,
            created_by=actor_id,
        )
        db.add(profile)
        db.flush()
        return profile.serialize()


def list_profiles(user_data: dict) -> dict:
    actor_id, project_id = _actor(user_data)
    with transaction_context() as db:
        profiles = (
            db.query(CalendarProfile)
            .filter(CalendarProfile.id_user == actor_id, CalendarProfile.id_proyect == project_id)
            .filter(CalendarProfile.deletion_date.is_(None))
            .order_by(CalendarProfile.id_calendar_profile)
            .all()
        )
        items = []
        for profile in profiles:
            payload = profile.serialize()
            payload["appointment_types"] = [
                item.serialize() for item in db.query(AppointmentType).filter(
                    AppointmentType.id_calendar_profile == profile.id_calendar_profile,
                    AppointmentType.deletion_date.is_(None),
                ).order_by(AppointmentType.id_appointment_type).all()
            ]
            payload["availability_rules"] = [
                item.serialize() for item in db.query(AvailabilityRule).filter(
                    AvailabilityRule.id_calendar_profile == profile.id_calendar_profile,
                    AvailabilityRule.deletion_date.is_(None),
                ).order_by(AvailabilityRule.weekday, AvailabilityRule.start_time).all()
            ]
            items.append(payload)
        return {"items": items, "total": len(items)}


def create_appointment_type(profile_id, payload: dict, user_data: dict) -> dict:
    with transaction_context() as db:
        profile = _profile_for_actor(db, profile_id, user_data)
        if not str(payload.get("name") or "").strip():
            raise AppError("errors.invalid_field", 400, {"field": "name"})
        provider = str(payload.get("meeting_provider") or "none").lower()
        if provider not in {"none", "google", "microsoft", "zoom"}:
            raise AppError("errors.invalid_field", 400, {"field": "meeting_provider"})
        if provider != "none":
            raise AppError("errors.calendar_provider_not_configured", 501, {"provider": provider})
        record = AppointmentType(
            id_calendar_profile=profile.id_calendar_profile,
            name=str(payload["name"]).strip(),
            description=payload.get("description"),
            duration_minutes=_integer(payload.get("duration_minutes"), "duration_minutes", minimum=5, maximum=480),
            buffer_before_minutes=_integer(payload.get("buffer_before_minutes", 0), "buffer_before_minutes", maximum=240),
            buffer_after_minutes=_integer(payload.get("buffer_after_minutes", 0), "buffer_after_minutes", maximum=240),
            minimum_notice_minutes=_integer(payload.get("minimum_notice_minutes", 0), "minimum_notice_minutes", maximum=525600),
            booking_horizon_days=_integer(payload.get("booking_horizon_days", 60), "booking_horizon_days", minimum=1, maximum=365),
            meeting_provider=provider,
            created_by=profile.id_user,
        )
        db.add(record)
        try:
            db.flush()
        except IntegrityError as error:
            # Dos reservas del mismo horario a la vez: la restriccion de la base
            # (ex_appointment_no_overlap) la rechaza, y eso es un 409, no un 500.
            raise AppError("errors.appointment_slot_unavailable", 409) from error
        return record.serialize()


def create_availability_rule(profile_id, payload: dict, user_data: dict) -> dict:
    with transaction_context() as db:
        profile = _profile_for_actor(db, profile_id, user_data)
        weekday = _integer(payload.get("weekday"), "weekday", maximum=6)
        start = _parse_time(payload.get("start_time"), "start_time")
        end = _parse_time(payload.get("end_time"), "end_time")
        if start >= end:
            raise AppError("errors.invalid_field", 400, {"field": "end_time"})
        record = AvailabilityRule(
            id_calendar_profile=profile.id_calendar_profile,
            weekday=weekday,
            start_time=start,
            end_time=end,
            created_by=profile.id_user,
        )
        db.add(record)
        db.flush()
        return record.serialize()


def create_availability_override(profile_id, payload: dict, user_data: dict) -> dict:
    with transaction_context() as db:
        profile = _profile_for_actor(db, profile_id, user_data)
        is_available = bool(payload.get("is_available", False))
        start = _parse_time(payload.get("start_time"), "start_time") if is_available else None
        end = _parse_time(payload.get("end_time"), "end_time") if is_available else None
        if is_available and start >= end:
            raise AppError("errors.invalid_field", 400, {"field": "end_time"})
        record = AvailabilityOverride(
            id_calendar_profile=profile.id_calendar_profile,
            override_date=_parse_date(payload.get("override_date"), "override_date"),
            start_time=start,
            end_time=end,
            is_available=is_available,
            created_by=profile.id_user,
        )
        db.add(record)
        db.flush()
        return record.serialize()


def list_appointments(user_data: dict, *, status=None, date_from=None, date_to=None) -> dict:
    actor_id, project_id = _actor(user_data)
    with transaction_context() as db:
        query = (
            db.query(Appointment)
            .join(CalendarProfile, Appointment.id_calendar_profile == CalendarProfile.id_calendar_profile)
            .filter(CalendarProfile.id_user == actor_id, Appointment.id_proyect == project_id)
        )
        if status:
            query = query.filter(Appointment.status == str(status))
        if date_from:
            query = query.filter(Appointment.starts_at >= _parse_datetime(date_from, "date_from"))
        if date_to:
            query = query.filter(Appointment.starts_at <= _parse_datetime(date_to, "date_to"))
        records = query.order_by(Appointment.starts_at).limit(500).all()
        return {"items": [record.serialize(include_private=True) for record in records], "total": len(records)}


def public_calendar(code: str) -> dict:
    with transaction_context() as db:
        profile = _public_profile(db, code)
        types = (
            db.query(AppointmentType)
            .filter(AppointmentType.id_calendar_profile == profile.id_calendar_profile)
            .filter(AppointmentType.is_active.is_(True), AppointmentType.deletion_date.is_(None))
            .order_by(AppointmentType.id_appointment_type)
            .all()
        )
        return {"calendar_code": profile.calendar_code, "display_name": profile.display_name, "timezone": profile.timezone, "appointment_types": [_public_type_payload(item) for item in types]}


def _public_profile(db, code: str, *, for_update=False) -> CalendarProfile:
    query = (
        db.query(CalendarProfile)
        .filter(CalendarProfile.calendar_code == str(code).strip().lower())
        .filter(CalendarProfile.is_active.is_(True), CalendarProfile.deletion_date.is_(None))
    )
    if for_update:
        query = query.with_for_update()
    profile = query.first()
    if not profile:
        raise AppError("errors.resource_not_found", 404)
    return profile


def _appointment_type(db, profile: CalendarProfile, type_id) -> AppointmentType:
    record = (
        db.query(AppointmentType)
        .filter(AppointmentType.id_appointment_type == _integer(type_id, "id_appointment_type", minimum=1))
        .filter(AppointmentType.id_calendar_profile == profile.id_calendar_profile)
        .filter(AppointmentType.is_active.is_(True), AppointmentType.deletion_date.is_(None))
        .first()
    )
    if not record:
        raise AppError("errors.resource_not_found", 404)
    return record


def _a_utc(valor: datetime) -> datetime:
    """UTC de un instante. Si la base lo devuelve con su zona (America/Mexico_City)
    se CONVIERTE; solo uno sin zona se asume UTC. `replace(tzinfo=utc)` sobre uno
    con zona lo corria horas y los horarios ya agendados seguian ofreciendose."""
    return valor.replace(tzinfo=timezone.utc) if valor.tzinfo is None else valor.astimezone(timezone.utc)


def _slots(db, profile: CalendarProfile, appointment_type: AppointmentType, start_date: date, end_date: date, now: datetime) -> list[datetime]:
    if end_date < start_date or (end_date - start_date).days > 31:
        raise AppError("errors.invalid_field", 400, {"field": "date_to"})
    zone = _zone(profile.timezone)
    latest = now + timedelta(days=appointment_type.booking_horizon_days)
    earliest = now + timedelta(minutes=appointment_type.minimum_notice_minutes)
    rules = db.query(AvailabilityRule).filter(
        AvailabilityRule.id_calendar_profile == profile.id_calendar_profile,
        AvailabilityRule.is_active.is_(True),
        AvailabilityRule.deletion_date.is_(None),
    ).all()
    overrides = db.query(AvailabilityOverride).filter(
        AvailabilityOverride.id_calendar_profile == profile.id_calendar_profile,
        AvailabilityOverride.override_date.between(start_date, end_date),
        AvailabilityOverride.deletion_date.is_(None),
    ).all()
    overrides_by_date = {}
    for override in overrides:
        overrides_by_date.setdefault(override.override_date, []).append(override)

    duration = timedelta(minutes=appointment_type.duration_minutes)
    slots = []
    current_date = start_date
    while current_date <= end_date:
        day_overrides = overrides_by_date.get(current_date, [])
        if day_overrides:
            windows = [(item.start_time, item.end_time) for item in day_overrides if item.is_available and item.start_time and item.end_time]
        else:
            windows = [(item.start_time, item.end_time) for item in rules if item.weekday == current_date.weekday()]
        for window_start, window_end in windows:
            candidate = datetime.combine(current_date, window_start, zone).astimezone(timezone.utc)
            boundary = datetime.combine(current_date, window_end, zone).astimezone(timezone.utc)
            while candidate + duration <= boundary:
                if earliest <= candidate <= latest:
                    slots.append(candidate)
                candidate += duration
        current_date += timedelta(days=1)

    if not slots:
        return []
    range_start = min(slots) - timedelta(minutes=appointment_type.buffer_before_minutes)
    range_end = max(slots) + duration + timedelta(minutes=appointment_type.buffer_after_minutes)
    appointments = db.query(Appointment).filter(
        Appointment.id_calendar_profile == profile.id_calendar_profile,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.blocked_starts_at < range_end,
        Appointment.blocked_ends_at > range_start,
    ).all()
    before = timedelta(minutes=appointment_type.buffer_before_minutes)
    after = timedelta(minutes=appointment_type.buffer_after_minutes)
    return [
        slot for slot in slots
        if not any(slot - before < _a_utc(item.blocked_ends_at) and slot + duration + after > _a_utc(item.blocked_starts_at) for item in appointments)
    ]


def list_slots(code: str, type_id, date_from, date_to, *, now=None) -> dict:
    with transaction_context() as db:
        profile = _public_profile(db, code)
        appointment_type = _appointment_type(db, profile, type_id)
        start_date = _parse_date(date_from, "date_from")
        end_date = _parse_date(date_to or date_from, "date_to")
        values = _slots(db, profile, appointment_type, start_date, end_date, now or datetime.now(timezone.utc))
        return {"timezone": profile.timezone, "slots": [value.isoformat().replace("+00:00", "Z") for value in values]}


def book_appointment(code: str, payload: dict, *, now=None) -> dict:
    starts_at = _parse_datetime(payload.get("starts_at"), "starts_at")
    guest_name = str(payload.get("guest_name") or "").strip()
    guest_email = str(payload.get("guest_email") or "").strip().lower()
    if not guest_name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", guest_email):
        raise AppError("errors.invalid_field", 400, {"field": "guest_name" if not guest_name else "guest_email"})

    appointment_id = None
    with transaction_context() as db:
        profile = _public_profile(db, code, for_update=True)
        appointment_type = _appointment_type(db, profile, payload.get("id_appointment_type"))
        available = _slots(db, profile, appointment_type, starts_at.astimezone(_zone(profile.timezone)).date(), starts_at.astimezone(_zone(profile.timezone)).date(), now or datetime.now(timezone.utc))
        if starts_at not in available:
            raise AppError("errors.appointment_slot_unavailable", 409)
        token = secrets.token_urlsafe(32)
        record = Appointment(
            id_calendar_profile=profile.id_calendar_profile,
            id_appointment_type=appointment_type.id_appointment_type,
            id_proyect=profile.id_proyect,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_notes=str(payload.get("guest_notes") or "").strip() or None,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=appointment_type.duration_minutes),
            blocked_starts_at=starts_at - timedelta(minutes=appointment_type.buffer_before_minutes),
            blocked_ends_at=starts_at + timedelta(minutes=appointment_type.duration_minutes + appointment_type.buffer_after_minutes),
            guest_timezone=str(payload.get("timezone") or profile.timezone),
            status="confirmed",
            meeting_provider=appointment_type.meeting_provider,
            external_status="not_required" if appointment_type.meeting_provider == "none" else "pending",
            management_token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            created_by=profile.id_user,
        )
        _zone(record.guest_timezone)
        db.add(record)
        db.flush()
        appointment_id = record.id_appointment
        response = _public_appointment_payload(record)
        response["management_token"] = token
    if os.getenv("TESTING", "0") != "1":
        try:
            from app.jobs.tasks_appointments import send_appointment_email
            send_appointment_email.delay(appointment_id, False)
        except Exception:
            pass
    return response


def cancel_appointment(management_token: str) -> dict:
    token_hash = hashlib.sha256(str(management_token or "").encode("utf-8")).hexdigest()
    with transaction_context() as db:
        record = db.query(Appointment).filter(Appointment.management_token_hash == token_hash).with_for_update().first()
        if not record:
            raise AppError("errors.resource_not_found", 404)
        if record.status == "cancelled":
            return _public_appointment_payload(record)
        if record.status not in ACTIVE_STATUSES:
            raise AppError("errors.appointment_invalid_transition", 409, {"status": record.status})
        record.status = "cancelled"
        record.cancellation_date = datetime.now(timezone.utc)
        record.external_status = "cancellation_pending" if record.meeting_provider != "none" else "not_required"
        db.flush()
        return _public_appointment_payload(record)