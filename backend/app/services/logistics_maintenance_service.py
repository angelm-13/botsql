from datetime import date
from decimal import Decimal, InvalidOperation

from app.models import LogisticsMaintenance, LogisticsUnit
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsMaintenanceService(CrudService):
    model = LogisticsMaintenance
    primary_key = 'id_logistics_maintenance'
    entity_name = 'logistics_maintenance'

    @staticmethod
    def _parse_date(value, field: str):
        if value in (None, ''):
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).split('T', 1)[0])
        except ValueError:
            raise AppError('errors.invalid_field', status_code=400, meta={'field': field})

    @classmethod
    def _validate(cls, payload: dict, current: dict | None = None) -> dict:
        payload = dict(payload or {})
        unit_id = payload.get('id_logistics_unit')
        if unit_id is not None:
            try:
                unit_id = int(unit_id)
            except (TypeError, ValueError):
                raise AppError('validations.logistics_maintenance.unit.invalid', status_code=400, meta={'field': 'id_logistics_unit'})
            with transaction_context() as session:
                unit = session.get(LogisticsUnit, unit_id)
                if not unit or unit.deletion_date is not None:
                    raise AppError('validations.logistics_maintenance.unit.invalid', status_code=400, meta={'field': 'id_logistics_unit'})
            payload['id_logistics_unit'] = unit_id
        elif current is None:
            raise AppError('validations.logistics_maintenance.unit.required', status_code=400, meta={'field': 'id_logistics_unit'})

        if 'cost' in payload and payload['cost'] not in (None, ''):
            try:
                if Decimal(str(payload['cost'])) < 0:
                    raise AppError('validations.logistics_maintenance.cost.invalid', status_code=400, meta={'field': 'cost'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'cost'})

        status = payload.get('status', (current or {}).get('status', 'abierta'))
        if status not in {'abierta', 'en proceso', 'cerrada'}:
            raise AppError('validations.logistics_maintenance.status.invalid', status_code=400, meta={'field': 'status'})
        scheduled_at = cls._parse_date(payload.get('scheduled_at', (current or {}).get('scheduled_at')), 'scheduled_at')
        closed_at = cls._parse_date(payload.get('closed_at', (current or {}).get('closed_at')), 'closed_at')
        if closed_at and scheduled_at and closed_at < scheduled_at:
            raise AppError('validations.logistics_maintenance.closed_at.invalid', status_code=400, meta={'field': 'closed_at'})
        if status == 'cerrada' and closed_at is None:
            raise AppError('validations.logistics_maintenance.closed_at.required', status_code=400, meta={'field': 'closed_at'})
        if status != 'cerrada' and closed_at is not None:
            raise AppError('validations.logistics_maintenance.closed_at.inconsistent', status_code=400, meta={'field': 'closed_at'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        current = cls.get(item_id)
        return super().update(item_id, cls._validate(payload, current=current), user_id=user_id)