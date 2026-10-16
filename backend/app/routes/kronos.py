from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.services.attendance_record_service import (
    checadas_en_rango,
    como_eventos_kronos,
    desligar_empleado,
    empleados_para_ligar,
    importar_eventos_kronos,
    ligar_empleado,
    nombres_de_empleados,
    vinculos_de_empleados,
)
from app.services.kronos_service import (
    KronosDeviceError,
    KronosService,
    attendance_statistics,
    summarize_attendance,
)
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError


bp_kronos = Blueprint("kronos", __name__, url_prefix="/kronos")


def _payload() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AppError("errors.invalid_payload", 400)
    missing = [field for field in ("deviceUrl", "username", "password") if not payload.get(field)]
    if missing:
        raise AppError("errors.invalid_field", 400, {"fields": missing})
    return payload


def _service(payload: dict) -> KronosService:
    try:
        return KronosService(payload)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": "deviceUrl"}) from exc


def _validate_period(payload: dict) -> tuple[str, str]:
    start_time = str(payload.get("startTime") or "")
    end_time = str(payload.get("endTime") or "")
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"fields": ["startTime", "endTime"]}) from exc
    if start > end:
        raise AppError("errors.invalid_field", 400, {"field": "startTime"})
    return start_time, end_time


def _device_operation(operation):
    try:
        return operation()
    except KronosDeviceError as exc:
        raise AppError("errors.kronos_device_unavailable", 502) from exc


@bp_kronos.post("/attendance")
@token_required
@require_entity_permission("payroll_period", "read")
def attendance(_user_data):
    payload = _payload()
    start_time, end_time = _validate_period(payload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        events_future = executor.submit(_service(payload).fetch_attendance, start_time, end_time)
        people_future = executor.submit(_service(payload).fetch_people)
        events = _device_operation(events_future.result)
        people = _device_operation(people_future.result)
    report = summarize_attendance(events, people)
    return jsonify(
        {
            "events": events,
            "people": people,
            "report": report,
            "statistics": attendance_statistics(report),
        }
    )


@bp_kronos.post("/attendance/import")
@token_required
@require_entity_permission("attendance_record", "create")
def import_attendance(user_data):
    """Trae del checador las checadas del periodo y guarda las que falten."""
    payload = _payload()
    start_time, end_time = _validate_period(payload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        events_future = executor.submit(_service(payload).fetch_attendance, start_time, end_time)
        people_future = executor.submit(_service(payload).fetch_people)
        events = _device_operation(events_future.result)
        people = _device_operation(people_future.result)
    return jsonify(
        importar_eventos_kronos(events, payload["deviceUrl"], user_data.get("id_user"), people)
    )


def _saved_period() -> tuple[date, date]:
    try:
        start = date.fromisoformat(str(request.args.get("startDate") or ""))
        end = date.fromisoformat(str(request.args.get("endDate") or ""))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"fields": ["startDate", "endDate"]}) from exc
    if start > end:
        raise AppError("errors.invalid_field", 400, {"field": "startDate"})
    return start, end


@bp_kronos.get("/attendance/saved")
@token_required
@require_entity_permission("attendance_record", "read")
def saved_attendance(_user_data):
    """Lo mismo que /attendance, pero leido de la base: no necesita el checador."""
    start, end = _saved_period()
    records = checadas_en_rango(start, end)
    events = como_eventos_kronos(records, nombres_de_empleados(records))
    report = summarize_attendance(events)
    return jsonify(
        {
            "events": events,
            "report": report,
            "statistics": attendance_statistics(report),
        }
    )


@bp_kronos.get("/employee-links")
@token_required
@require_entity_permission("attendance_employee_link", "read")
def employee_links(_user_data):
    """Que empleado del sistema es cada numero del checador."""
    return jsonify({"links": vinculos_de_empleados()})


@bp_kronos.get("/employee-options")
@token_required
@require_entity_permission("attendance_employee_link", "read")
def employee_options(_user_data):
    """Solo los usuarios marcados como empleados: a ellos se les puede ligar un numero."""
    return jsonify({"employees": empleados_para_ligar()})


@bp_kronos.put("/employee-links/<string:employee_no>")
@token_required
@require_entity_permission("attendance_employee_link", "update")
def link_employee(user_data, employee_no: str):
    payload = request.get_json(silent=True) or {}
    return jsonify(ligar_empleado(employee_no, payload.get("id_user"), user_data.get("id_user")))


@bp_kronos.delete("/employee-links/<string:employee_no>")
@token_required
@require_entity_permission("attendance_employee_link", "delete")
def unlink_employee(user_data, employee_no: str):
    return jsonify(desligar_empleado(employee_no, user_data.get("id_user")))


@bp_kronos.post("/people")
@token_required
@require_entity_permission("payroll_period", "read")
def people(_user_data):
    service = _service(_payload())
    return jsonify({"people": _device_operation(service.fetch_people)})


@bp_kronos.put("/people")
@token_required
@require_entity_permission("payroll_period", "update")
def save_person(_user_data):
    payload = _payload()
    person = payload.get("person")
    if not isinstance(person, dict) or not person.get("employeeNo") or not person.get("name"):
        raise AppError(
            "errors.invalid_field", 400, {"fields": ["person.employeeNo", "person.name"]}
        )
    return jsonify(_device_operation(lambda: _service(payload).save_person(person)))


@bp_kronos.delete("/people/<string:employee_no>")
@token_required
@require_entity_permission("payroll_period", "delete")
def delete_person(_user_data, employee_no: str):
    service = _service(_payload())
    return jsonify(_device_operation(lambda: service.delete_person(employee_no)))
