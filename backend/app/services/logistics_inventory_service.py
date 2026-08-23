from decimal import Decimal, InvalidOperation

from app.models import CustomerSupplier, LogisticsInventory, LogisticsLocation
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsInventoryService(CrudService):
    model = LogisticsInventory
    primary_key = 'id_logistics_inventory'
    entity_name = 'logistics_inventory'

    @classmethod
    def _validate(cls, payload: dict, *, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._validate_fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', creating)
        cls._validate_fk(payload, 'id_logistics_location', LogisticsLocation, 'location', creating)
        if 'quantity' in payload and payload['quantity'] not in (None, ''):
            try:
                if Decimal(str(payload['quantity'])) < 0:
                    raise AppError('validations.logistics_inventory.quantity.invalid', status_code=400, meta={'field': 'quantity'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'quantity'})
        if 'status' in payload and payload['status'] not in {'activo', 'pendiente_surtido', 'surtido', 'inactivo'}:
            raise AppError('validations.logistics_inventory.status.invalid', status_code=400, meta={'field': 'status'})
        return payload

    @staticmethod
    def _validate_fk(payload: dict, field: str, model, label: str, creating: bool) -> None:
        value = payload.get(field)
        if value in (None, ''):
            if creating:
                raise AppError(f'validations.logistics_inventory.{label}.required', status_code=400, meta={'field': field})
            return
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise AppError(f'validations.logistics_inventory.{label}.invalid', status_code=400, meta={'field': field})
        with transaction_context() as session:
            item = session.get(model, value)
            if not item or item.deletion_date is not None or (label == 'client' and item.type != 'client'):
                raise AppError(f'validations.logistics_inventory.{label}.invalid', status_code=400, meta={'field': field})
        payload[field] = value

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, creating=True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)