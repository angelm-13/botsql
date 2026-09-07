from sqlalchemy import func, select

from app.models import Invoice, Product
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class ProductService(CrudService):
    model = Product
    primary_key = 'id_product'
    entity_name = 'product'

    @classmethod
    def _rechazar_lot_control(cls, payload: dict) -> dict:
        """El control por lote no se enciende escribiendo la columna.

        Encenderlo en un producto que YA tiene existencia deja esa existencia
        fuera de todo lote, y como la salida se sirve de los lotes, esas unidades
        no se pueden despachar: el saldo dice que estan y los lotes dicen que no.
        Medido al probar contra Postgres, donde el cuadre salio en falso con
        saldo 1 y 0 en lotes.

        Para eso esta `POST /product/<id>/lot-control`, que enciende y crea el
        lote de apertura con lo que ya habia, en la misma transaccion.
        """
        if 'lot_control' in (payload or {}):
            raise AppError(
                'errors.lot_control_needs_its_own_endpoint',
                400,
                {'field': 'lot_control',
                 'use': 'POST /product/<id_product>/lot-control'},
            )
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._rechazar_lot_control(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._rechazar_lot_control(payload),
                              user_id=user_id)

    @staticmethod
    def _project_id(user_data: dict) -> int | None:
        if user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'):
            return None
        try:
            return int(user_data.get('id_proyect'))
        except (TypeError, ValueError):
            raise AppError('errors.project_scope_required', status_code=403)

    @classmethod
    def list_scoped(cls, user_data: dict, page: int = 1, per_page: int = 20, filters: dict | None = None, sort: str | None = None):
        project_id = cls._project_id(user_data)
        if project_id is None:
            return cls.list(page=page, per_page=per_page, filters=filters, sort=sort)

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(Product).join(Invoice, Product.id_invoice == Invoice.id_invoice).where(Invoice.id_proyect == project_id)
            for key, value in filters.items():
                if not hasattr(Product, key) or value in (None, ''):
                    continue
                column = getattr(Product, key)
                stmt = stmt.where(column.ilike(f'%{value}%') if isinstance(value, str) else column == value)
            if sort and hasattr(Product, sort.lstrip('-')):
                column = getattr(Product, sort.lstrip('-'))
                stmt = stmt.order_by(column.desc() if sort.startswith('-') else column.asc())
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            items = session.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
            return {
                'items': [item.serialize() for item in items],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
            }

    @classmethod
    def require_record_scope(cls, item_id, user_data: dict) -> None:
        project_id = cls._project_id(user_data)
        if project_id is None:
            return
        with transaction_context() as session:
            exists = session.scalar(
                select(Product.id_product)
                .join(Invoice, Product.id_invoice == Invoice.id_invoice)
                .where(Product.id_product == item_id, Invoice.id_proyect == project_id)
            )
            if exists is None:
                raise AppError('errors.resource_not_found', status_code=404)

    @classmethod
    def require_invoice_scope(cls, invoice_id, user_data: dict) -> None:
        project_id = cls._project_id(user_data)
        if project_id is None:
            return
        try:
            invoice_id = int(invoice_id)
        except (TypeError, ValueError):
            raise AppError('errors.invalid_field', status_code=400, meta={'field': 'id_invoice'})
        with transaction_context() as session:
            exists = session.scalar(
                select(Invoice.id_invoice).where(
                    Invoice.id_invoice == invoice_id,
                    Invoice.id_proyect == project_id,
                )
            )
            if exists is None:
                raise AppError('errors.resource_not_found', status_code=404)
