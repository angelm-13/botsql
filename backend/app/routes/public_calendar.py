from __future__ import annotations

import time
from collections import defaultdict, deque

from flask import Blueprint, jsonify, request

from app.services.appointment_service import book_appointment, cancel_appointment, list_slots, public_calendar
from app.utils.errors import AppError


bp_public_calendar = Blueprint("public_calendar", __name__, url_prefix="/public/calendars")
bp_public_appointments = Blueprint("public_appointments", __name__, url_prefix="/public/appointments")
_rate_limit_hits = defaultdict(deque)


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() or request.remote_addr or "")[:45]


def _enforce_rate(action: str, limit: int, seconds: int) -> None:
    key = f"{action}:{_client_ip()}"
    now = time.time()
    hits = _rate_limit_hits[key]
    while hits and now - hits[0] >= seconds:
        hits.popleft()
    if len(hits) >= limit:
        raise AppError("errors.rate_limit_exceeded", 429)
    hits.append(now)


@bp_public_calendar.route("/<code>", methods=["GET"])
def get_public_calendar(code):
    _enforce_rate("calendar", 120, 60)
    return jsonify(public_calendar(code))


@bp_public_calendar.route("/<code>/slots", methods=["GET"])
def get_public_slots(code):
    _enforce_rate("slots", 120, 60)
    return jsonify(list_slots(code, request.args.get("appointment_type_id"), request.args.get("date_from"), request.args.get("date_to")))


@bp_public_calendar.route("/<code>/appointments", methods=["POST"])
def post_public_appointment(code):
    _enforce_rate("booking", 10, 60)
    return jsonify(book_appointment(code, request.get_json() or {})), 201


@bp_public_calendar.route("/appointments/<management_token>/cancel", methods=["POST"])
def post_cancel_appointment(management_token):
    _enforce_rate("cancellation", 20, 60)
    return jsonify(cancel_appointment(management_token))


@bp_public_appointments.route("/<management_token>/cancel", methods=["POST"])
def post_cancel_appointment_canonical(management_token):
    _enforce_rate("cancellation", 20, 60)
    return jsonify(cancel_appointment(management_token))