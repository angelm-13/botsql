from sqlalchemy import Enum

from app.models import Permission
from app.services.base_service import CrudService


class PermissionService(CrudService):
    model = Permission
    primary_key = 'id_permission'
    entity_name = 'permission'

    @classmethod
    def list(cls, page: int = 1, per_page: int = 20, filters: dict | None = None,
             sort: str | None = None, q: str | None = None):
        """Solo los roles vigentes.

        El CRUD generico no filtra la baja logica -- a diferencia de
        `EntityPermissionService`, que si la filtra por el mismo motivo--, asi
        que un rol retirado (ej. "Jefe de almacen", fusionado en Almacenista)
        seguia apareciendo en el selector del Gestor de roles y en el selector
        de rol al dar de alta un usuario.
        """
        from sqlalchemy import func, select

        from app.models.session import transaction_context

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(cls.model).where(cls.model.deletion_date.is_(None))
            busqueda = cls._busqueda_libre(q)
            if busqueda is not None:
                stmt = stmt.where(busqueda)
            for clave, valor in filters.items():
                if not hasattr(cls.model, clave) or valor in (None, ''):
                    continue
                columna = getattr(cls.model, clave)
                model_column = cls._columns().get(clave)
                if isinstance(valor, str) and not (model_column is not None and isinstance(model_column.type, Enum)):
                    stmt = stmt.where(columna.ilike(f'%{valor}%'))
                else:
                    stmt = stmt.where(columna == valor)
            if sort and hasattr(cls.model, sort.lstrip('-')):
                col = getattr(cls.model, sort.lstrip('-'))
                stmt = stmt.order_by(col.desc() if sort.startswith('-') else col.asc())
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            filas = session.scalars(
                stmt.offset((page - 1) * per_page).limit(per_page)
            ).all()
            return {
                'items': [f.serialize() for f in filas],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
            }
