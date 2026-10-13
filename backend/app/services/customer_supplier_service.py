from decimal import Decimal, InvalidOperation

from app.models import CustomerSupplier
from app.services.base_service import CrudService
from app.models.session import transaction_context
from app.utils.errors import AppError


class CustomerSupplierService(CrudService):
    model = CustomerSupplier
    primary_key = 'id_customer_supplier'
    entity_name = 'customer_supplier'
    logistics_sla_levels = {'standard', 'premium'}

    @classmethod
    def options(cls) -> list[dict]:
        """Solo id+nombre, para selectores como el de "Cliente" al crear un
        proyecto. A proposito no pasa por `_visible_response_fields_for_actor`
        ni exige el permiso de lectura completo de customer_supplier -- un
        Supervisor no debe ver el CRM completo (razon social, RFC, contacto),
        pero si necesita poder elegir un cliente al crear su propio proyecto.
        """
        with transaction_context() as session:
            filas = (
                session.query(CustomerSupplier.id_customer_supplier, CustomerSupplier.name)
                .filter(CustomerSupplier.deletion_date.is_(None))
                .order_by(CustomerSupplier.name)
                .all()
            )
            return [{'id_customer_supplier': fila[0], 'name': fila[1]} for fila in filas]

    @classmethod
    def _validate_logistics_fields(cls, payload: dict) -> dict:
        payload = dict(payload or {})
        if 'sla_level' in payload:
            sla_level = str(payload.get('sla_level') or '').strip().lower()
            if sla_level not in cls.logistics_sla_levels:
                raise AppError(
                    'validations.customer_supplier.sla_level.invalid',
                    status_code=400,
                    meta={'field': 'sla_level'},
                )
            payload['sla_level'] = sla_level
        if 'credit_limit' in payload:
            try:
                credit_limit = Decimal(str(payload.get('credit_limit') or '0'))
            except InvalidOperation as exc:
                raise AppError(
                    'validations.customer_supplier.credit_limit.invalid',
                    status_code=400,
                    meta={'field': 'credit_limit'},
                ) from exc
            if credit_limit < 0:
                raise AppError(
                    'validations.customer_supplier.credit_limit.negative',
                    status_code=400,
                    meta={'field': 'credit_limit'},
                )
            payload['credit_limit'] = credit_limit
        return payload

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

    # El RFC se guarda en mayusculas y sin espacios, para que la busqueda y la
    # importacion por XML lo encuentren sin importar como se capturo.
    #
    # A proposito NO se rechaza un RFC repetido: en multiemisor una misma razon
    # social puede tener varias fichas emisoras (torredigital-prod: fichas 1 y 31,
    # las dos con facturas, folios y CSD propios). La regla de unicidad (95c5e64 de
    # initAngm) queda pendiente de decidir con Tanya si se acota a quien no emite.
    @classmethod
    def _normalizar_rfc(cls, payload: dict) -> dict:
        if 'tax_id' not in payload or payload.get('tax_id') in (None, ''):
            return payload
        payload = dict(payload)
        payload['tax_id'] = ''.join(str(payload['tax_id']).split()).upper()
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        if not str((payload or {}).get('type') or '').strip():
            raise AppError('validations.customer_supplier.type.required', 400, meta={'field': 'type'})
        payload = cls._normalizar_rfc(payload)
        payload = cls._validate_logistics_fields(payload)
        is_principal = cls._as_boolean(payload.pop('is_principal', False))
        created = super().create(payload, user_id=user_id)
        if is_principal:
            return cls._set_principal_state(created['id_customer_supplier'], True)
        return created

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = cls._normalizar_rfc(payload)
        payload = cls._validate_logistics_fields(payload)
        has_principal_value = 'is_principal' in payload
        is_principal = cls._as_boolean(payload.pop('is_principal', False))
        updated = super().update(item_id, payload, user_id=user_id)
        if has_principal_value:
            return cls._set_principal_state(item_id, is_principal)
        return updated
