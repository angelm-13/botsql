"""Horarios de trabajo (work_schedule) y sus validaciones.

Los servicios de las cuatro tablas de horarios viven en este modulo y en los
tres que lo reexportan (work_schedule_day_service, employee_schedule_service,
payroll_holiday_service), que es como las rutas genericas los importan. Las
reglas se validan aqui y no en la pantalla para que valgan igual por la API.
"""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select

from app.models import EmployeeSchedule, PayrollHoliday, User, WorkSchedule, WorkScheduleDay
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


def _hora(valor, campo) -> time:
    if isinstance(valor, time):
        return valor
    try:
        return time.fromisoformat(str(valor).strip()[:8])
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _fecha(valor, campo, opcional=False):
    if valor in (None, ""):
        if opcional:
            return None
        raise AppError("errors.invalid_field", 400, {"field": campo})
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _entero(valor, campo) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


class WorkScheduleService(CrudService):
    model = WorkSchedule
    primary_key = 'id_work_schedule'
    entity_name = 'work_schedule'

    @classmethod
    def _validar(cls, datos: dict) -> None:
        if not str(datos.get("schedule_name") or "").strip():
            raise AppError("errors.invalid_field", 400, {"field": "schedule_name"})
        tolerancia = _entero(datos.get("tolerance_minutes", 10), "tolerance_minutes")
        if not 0 <= tolerancia <= 240:
            raise AppError("errors.invalid_field", 400, {"field": "tolerance_minutes"})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._validar({**cls.get(item_id), **dict(payload or {})})
        return super().update(item_id, payload, user_id=user_id)


class WorkScheduleDayService(CrudService):
    """Un dia laboral de un horario: un solo renglon vivo por dia de la semana."""

    model = WorkScheduleDay
    primary_key = 'id_work_schedule_day'
    entity_name = 'work_schedule_day'

    @classmethod
    def _preparar(cls, datos: dict, excluir_id=None) -> dict:
        dia = _entero(datos.get("weekday"), "weekday")
        if not 0 <= dia <= 6:
            raise AppError("errors.invalid_field", 400, {"field": "weekday"})
        inicio = _hora(datos.get("start_time"), "start_time")
        fin = _hora(datos.get("end_time"), "end_time")
        if fin <= inicio:
            raise AppError("errors.invalid_field", 400, {"field": "end_time"})
        horario = _entero(datos.get("id_work_schedule"), "id_work_schedule")
        with transaction_context() as db:
            if db.get(WorkSchedule, horario) is None:
                raise AppError("errors.invalid_field", 400, {"field": "id_work_schedule"})
            for otro in db.scalars(select(WorkScheduleDay)
                                   .where(WorkScheduleDay.id_work_schedule == horario)
                                   .where(WorkScheduleDay.weekday == dia)
                                   .where(WorkScheduleDay.deletion_date.is_(None))):
                if excluir_id is None or str(otro.id_work_schedule_day) != str(excluir_id):
                    raise AppError("errors.work_schedule_day_duplicate", 409, {"weekday": dia})
        return {"start_time": inicio, "end_time": fin}

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.update(cls._preparar(payload))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.update(cls._preparar({**cls.get(item_id), **payload}, excluir_id=item_id))
        return super().update(item_id, payload, user_id=user_id)


class EmployeeScheduleService(CrudService):
    """Asignacion de horario a un empleado; las vigencias de una persona no se enciman."""

    model = EmployeeSchedule
    primary_key = 'id_employee_schedule'
    entity_name = 'employee_schedule'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        id_user = _entero(datos.get("id_user"), "id_user")
        horario = _entero(datos.get("id_work_schedule"), "id_work_schedule")
        desde = _fecha(datos.get("valid_from"), "valid_from")
        hasta = _fecha(datos.get("valid_to"), "valid_to", opcional=True)
        if hasta is not None and hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "valid_to"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            if db.get(WorkSchedule, horario) is None:
                raise AppError("errors.invalid_field", 400, {"field": "id_work_schedule"})
            for otro in db.scalars(select(EmployeeSchedule)
                                   .where(EmployeeSchedule.id_user == id_user)
                                   .where(EmployeeSchedule.deletion_date.is_(None))):
                if excluir_id is not None and str(otro.id_employee_schedule) == str(excluir_id):
                    continue
                if desde <= (otro.valid_to or date.max) and otro.valid_from <= (hasta or date.max):
                    raise AppError("errors.employee_schedule_overlap", 409, {
                        "id_employee_schedule": otro.id_employee_schedule,
                        "valid_from": otro.valid_from.isoformat(),
                        "valid_to": otro.valid_to.isoformat() if otro.valid_to else None})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._validar({**cls.get(item_id), **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)


class PayrollHolidayService(CrudService):
    """Dias de descanso obligatorio; uno por fecha."""

    model = PayrollHoliday
    primary_key = 'id_payroll_holiday'
    entity_name = 'payroll_holiday'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        fecha = _fecha(datos.get("holiday_date"), "holiday_date")
        if not str(datos.get("description") or "").strip():
            raise AppError("errors.invalid_field", 400, {"field": "description"})
        with transaction_context() as db:
            otro = db.scalars(select(PayrollHoliday).where(PayrollHoliday.holiday_date == fecha)).first()
            if otro is not None and (excluir_id is None or str(otro.id_payroll_holiday) != str(excluir_id)):
                raise AppError("errors.payroll_holiday_duplicate", 409, {"holiday_date": fecha.isoformat()})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._validar({**cls.get(item_id), **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)
