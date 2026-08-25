from decimal import Decimal, InvalidOperation

from app.models import LogisticsOperator
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsOperatorService(CrudService):
    model = LogisticsOperator
    primary_key = 'id_logistics_operator'
    entity_name = 'logistics_operator'

    @classmethod
    def _validate(cls, payload: dict) -> dict:
        payload = dict(payload or {})
        if 'performance_score' in payload and payload['performance_score'] not in (None, ''):
            try:
                if Decimal(str(payload['performance_score'])) < 0:
                    raise AppError('validations.logistics_operator.performance_score.invalid', status_code=400, meta={'field': 'performance_score'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'performance_score'})
        if 'status' in payload and payload['status'] not in {'activo', 'inactivo'}:
            raise AppError('validations.logistics_operator.status.invalid', status_code=400, meta={'field': 'status'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)