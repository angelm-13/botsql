from decimal import Decimal, InvalidOperation

from app.models import CustomerSupplier, LogisticsRate
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsRateService(CrudService):
    model = LogisticsRate
    primary_key = 'id_logistics_rate'
    entity_name = 'logistics_rate'

    @staticmethod
    def _validate_client(payload: dict) -> dict:
        payload = dict(payload or {})
        client_id = payload.get('id_customer_supplier')
        if client_id in (None, ''):
            raise AppError('validations.logistics_rate.client.required', status_code=400, meta={'field': 'id_customer_supplier'})
        with transaction_context() as session:
            client = session.get(CustomerSupplier, int(client_id))
            if not client or client.deletion_date is not None or client.type != 'client':
                raise AppError('validations.logistics_rate.client.invalid', status_code=400, meta={'field': 'id_customer_supplier'})
        payload['id_customer_supplier'] = int(client_id)
        return payload

    @staticmethod
    def _validate_rate(payload: dict) -> dict:
        payload = dict(payload or {})
        if 'amount' in payload:
            try:
                if Decimal(str(payload['amount'])) < 0:
                    raise AppError('validations.logistics_rate.amount.invalid', status_code=400, meta={'field': 'amount'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'amount'})
        if 'currency' in payload:
            currency = str(payload['currency'] or '').upper()
            if currency not in {'MXN', 'USD'}:
                raise AppError('validations.logistics_rate.currency.invalid', status_code=400, meta={'field': 'currency'})
            payload['currency'] = currency
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate_rate(cls._validate_client(payload)), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        if 'id_customer_supplier' in payload:
            payload = cls._validate_client(payload)
        return super().update(item_id, cls._validate_rate(payload), user_id=user_id)