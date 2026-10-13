import re

from sqlalchemy import func

from app.models import CustomerContact, CustomerSupplier
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class CustomerContactService(CrudService):
    model = CustomerContact
    primary_key = 'id_customer_contact'
    entity_name = 'customer_contact'

    @staticmethod
    def _validate_customer(payload: dict) -> dict:
        payload = dict(payload or {})
        customer_id = payload.get('id_customer_supplier')
        if customer_id in (None, ''):
            raise AppError('validations.customer_contact.customer.required', status_code=400, meta={'field': 'id_customer_supplier'})
        with transaction_context() as session:
            customer = session.get(CustomerSupplier, int(customer_id))
            if not customer or customer.deletion_date is not None or customer.type != 'client':
                raise AppError('validations.customer_contact.customer.invalid', status_code=400, meta={'field': 'id_customer_supplier'})
        payload['id_customer_supplier'] = int(customer_id)
        CustomerContactService._validar_correo(payload)
        return payload

    @staticmethod
    def _validar_correo(payload: dict) -> None:
        correo = str(payload.get('email') or '').strip()
        if correo and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', correo):
            raise AppError('validations.customer_contact.email.invalid', status_code=400, meta={'field': 'email'})

    @staticmethod
    def _rechazar_duplicado(payload: dict, item_id=None) -> None:
        """Mismo cliente, mismo correo: es el mismo contacto."""
        correo = str(payload.get('email') or '').strip().lower()
        if not correo or payload.get('id_customer_supplier') is None:
            return
        with transaction_context() as session:
            consulta = session.query(CustomerContact.id_customer_contact).filter(
                CustomerContact.id_customer_supplier == payload['id_customer_supplier'],
                func.lower(CustomerContact.email) == correo,
                CustomerContact.deletion_date.is_(None))
            if item_id is not None:
                consulta = consulta.filter(CustomerContact.id_customer_contact != int(item_id))
            if consulta.first():
                raise AppError('validations.customer_contact.duplicate', status_code=409, meta={'field': 'email'})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = cls._validate_customer(payload)
        cls._rechazar_duplicado(payload)
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        if 'id_customer_supplier' in payload:
            payload = cls._validate_customer(payload)
        if payload.get('email'):
            cls._validar_correo(payload)
            cls._rechazar_duplicado({**cls.get(item_id), **payload}, item_id)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def options(cls) -> list[dict]:
        """"Empresa - Contacto", para el selector de "Cliente" del proyecto.

        Sin exigir el permiso completo de customer_contact -- mismo motivo
        que CustomerSupplierService.options(): quien puede crear un proyecto
        (Supervisor) no necesariamente puede ver/editar el catalogo de
        contactos del CRM.
        """
        with transaction_context() as session:
            filas = (
                session.query(
                    CustomerContact.id_customer_contact,
                    CustomerContact.id_customer_supplier,
                    CustomerContact.full_name,
                    CustomerSupplier.name,
                )
                .join(CustomerSupplier, CustomerSupplier.id_customer_supplier == CustomerContact.id_customer_supplier)
                .filter(CustomerContact.deletion_date.is_(None), CustomerContact.status == 'activo')
                .filter(CustomerSupplier.deletion_date.is_(None))
                .order_by(CustomerSupplier.name, CustomerContact.full_name)
                .all()
            )
            return [
                {
                    'id_customer_contact': fila[0],
                    'id_customer_supplier': fila[1],
                    'full_name': fila[2],
                    'label': f'{fila[3]} — {fila[2]}',
                }
                for fila in filas
            ]
