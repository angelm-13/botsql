from decimal import Decimal, InvalidOperation

from app.models import LogisticsLocation, LogisticsWarehouse
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsLocationService(CrudService):
    model = LogisticsLocation
    primary_key = 'id_logistics_location'
    entity_name = 'logistics_location'

    @classmethod
    def _validate(cls, payload: dict, *, creating: bool = False) -> dict:
        payload = dict(payload or {})
        warehouse_id = payload.get('id_logistics_warehouse')
        if warehouse_id in (None, ''):
            if creating:
                raise AppError('validations.logistics_location.warehouse.required', status_code=400, meta={'field': 'id_logistics_warehouse'})
        else:
            try:
                warehouse_id = int(warehouse_id)
            except (TypeError, ValueError):
                raise AppError('validations.logistics_location.warehouse.invalid', status_code=400, meta={'field': 'id_logistics_warehouse'})
            with transaction_context() as session:
                warehouse = session.get(LogisticsWarehouse, warehouse_id)
                if not warehouse or warehouse.deletion_date is not None:
                    raise AppError('validations.logistics_location.warehouse.invalid', status_code=400, meta={'field': 'id_logistics_warehouse'})
            payload['id_logistics_warehouse'] = warehouse_id
        if 'capacity' in payload and payload['capacity'] not in (None, ''):
            try:
                if Decimal(str(payload['capacity'])) < 0:
                    raise AppError('validations.logistics_location.capacity.invalid', status_code=400, meta={'field': 'capacity'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'capacity'})
        if 'status' in payload and payload['status'] not in {'activo', 'inactivo'}:
            raise AppError('validations.logistics_location.status.invalid', status_code=400, meta={'field': 'status'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, creating=True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)