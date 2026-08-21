from app.models import CustomerSupplier
from app.services.base_service import CrudService
from app.models.session import transaction_context
from app.utils.errors import AppError


class CustomerSupplierService(CrudService):
    model = CustomerSupplier
    primary_key = 'id_customer_supplier'
    entity_name = 'customer_supplier'

    @staticmethod
    def _as_boolean(value) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'on'}
        return bool(value)

    @classmethod
    def _set_principal_state(cls, item_id, enabled: bool):
        with transaction_context() as session:
            item = session.get(CustomerSupplier, item_id)
            if not item:
                raise AppError('errors.resource_not_found', status_code=404)
            if enabled and not str(item.tax_id or '').strip():
                raise AppError(
                    'validations.customer_supplier.principal_tax_id.required',
                    status_code=400,
                    meta={'field': 'tax_id'},
                )
            if enabled:
                session.query(CustomerSupplier).filter(
                    CustomerSupplier.id_customer_supplier != item.id_customer_supplier,
                    CustomerSupplier.is_principal.is_(True),
                ).update({'is_principal': False}, synchronize_session=False)
            item.is_principal = enabled
            session.flush()
            return item.serialize()

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        is_principal = cls._as_boolean(payload.pop('is_principal', False))
        created = super().create(payload, user_id=user_id)
        if is_principal:
            return cls._set_principal_state(created['id_customer_supplier'], True)
        return created

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        has_principal_value = 'is_principal' in payload
        is_principal = cls._as_boolean(payload.pop('is_principal', False))
        updated = super().update(item_id, payload, user_id=user_id)
        if has_principal_value:
            return cls._set_principal_state(item_id, is_principal)
        return updated
