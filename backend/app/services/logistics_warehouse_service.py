from decimal import Decimal, InvalidOperation

from app.models import LogisticsWarehouse
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsWarehouseService(CrudService):
    model = LogisticsWarehouse
    primary_key = 'id_logistics_warehouse'
    entity_name = 'logistics_warehouse'

    @classmethod
    def _validate(cls, payload: dict) -> dict:
        payload = dict(payload or {})
        if 'capacity' in payload and payload['capacity'] not in (None, ''):
            try:
                if Decimal(str(payload['capacity'])) < 0:
                    raise AppError('validations.logistics_warehouse.capacity.invalid', status_code=400, meta={'field': 'capacity'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'capacity'})
        if 'status' in payload and payload['status'] not in {'activo', 'inactivo'}:
            raise AppError('validations.logistics_warehouse.status.invalid', status_code=400, meta={'field': 'status'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)