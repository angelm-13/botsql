from decimal import Decimal, InvalidOperation

from app.models import LogisticsUnit
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsUnitService(CrudService):
    model = LogisticsUnit
    primary_key = 'id_logistics_unit'
    entity_name = 'logistics_unit'

    @classmethod
    def _validate(cls, payload: dict) -> dict:
        payload = dict(payload or {})
        for field in ('mileage', 'fuel_efficiency'):
            if field not in payload or payload[field] in (None, ''):
                continue
            try:
                if Decimal(str(payload[field])) < 0:
                    raise AppError(f'validations.logistics_unit.{field}.invalid', status_code=400, meta={'field': field})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': field})
        cls._validate_domain(payload, 'availability_status', {'disponible', 'en viaje', 'mantenimiento', 'fuera de servicio'})
        cls._validate_domain(payload, 'status', {'activo', 'inactivo'})
        return payload

    @classmethod
    def _validate_domain(cls, payload: dict, field: str, allowed: set[str]) -> None:
        if field in payload and payload[field] not in allowed:
            raise AppError(f'validations.logistics_unit.{field}.invalid', status_code=400, meta={'field': field})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)