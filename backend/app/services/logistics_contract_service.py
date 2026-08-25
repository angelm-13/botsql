from datetime import date, datetime

from app.models import CustomerSupplier, LogisticsContract
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsContractService(CrudService):
    model = LogisticsContract
    primary_key = 'id_logistics_contract'
    entity_name = 'logistics_contract'

    @staticmethod
    def _validate_client(payload: dict) -> dict:
        payload = dict(payload or {})
        client_id = payload.get('id_customer_supplier')
        if client_id in (None, ''):
            raise AppError('validations.logistics_contract.client.required', status_code=400, meta={'field': 'id_customer_supplier'})
        with transaction_context() as session:
            client = session.get(CustomerSupplier, int(client_id))
            if not client or client.deletion_date is not None or client.type != 'client':
                raise AppError('validations.logistics_contract.client.invalid', status_code=400, meta={'field': 'id_customer_supplier'})
        payload['id_customer_supplier'] = int(client_id)
        return payload

    @staticmethod
    def _as_date(value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).split('T', 1)[0].split(' ', 1)[0])
        except ValueError:
            raise AppError('errors.invalid_field', status_code=400, meta={'field': 'end_date'})

    @classmethod
    def _validate_dates(cls, payload: dict, current: dict | None = None) -> dict:
        payload = dict(payload or {})
        start_date = cls._as_date(payload.get('start_date', (current or {}).get('start_date')))
        end_date = cls._as_date(payload.get('end_date', (current or {}).get('end_date')))
        if start_date and end_date and end_date < start_date:
            raise AppError('validations.logistics_contract.end_date.invalid', status_code=400, meta={'field': 'end_date'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = cls._validate_dates(cls._validate_client(payload))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        if 'id_customer_supplier' in payload:
            payload = cls._validate_client(payload)
        return super().update(item_id, cls._validate_dates(payload, cls.get(item_id)), user_id=user_id)