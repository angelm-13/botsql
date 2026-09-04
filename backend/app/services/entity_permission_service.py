from app.models import EntityPermission
from app.services.base_service import CrudService


class EntityPermissionService(CrudService):
    model = EntityPermission
    primary_key = 'id_entity_permission'
    entity_name = 'entity_permission'

    # --- el gestor manda ----------------------------------------------------
    #
    # La decision es que el gestor de roles sea la autoridad sobre quien puede
    # que, y que el registro de modulos solo siembre lo que falta. Eso obliga a
    # dos cambios sobre el CRUD generico, y los dos estan aqui.

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        """Quitar un permiso lo marca de baja; no borra la fila.

        El CRUD generico hace `session.delete`, o sea borrado fisico. Con eso,
        una fila ausente puede significar dos cosas incompatibles: que nunca se
        sembro, o que el administrador la quito a proposito. El sembrado no
        podria distinguirlas y resucitaria en cada despliegue lo que alguien
        decidio retirar.

        Marcandola de baja, la ausencia significa "nueva" y la baja significa
        "la quitaron". El sembrado inserta lo primero y respeta lo segundo.

        De paso queda el rastro de quien retiro que permiso y cuando, que en una
        tabla de permisos vale mas que ahorrar una fila.
        """
        from datetime import datetime, timezone

        from app.models.session import transaction_context
        from app.utils.errors import AppError

        with transaction_context() as session:
            item = session.get(cls.model, item_id)
            if not item:
                raise AppError('errors.resource_not_found', status_code=404)
            if item.deletion_date is not None:
                # Ya estaba de baja: no se vuelve a fechar, para no perder
                # cuando se retiro de verdad.
                return {'message_key': 'success.deleted'}
            before = item.serialize()
            item.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
            cls._write_event_log(
                session,
                action='delete',
                actor_id=user_id,
                before=cls._format_audit_delete_before(before),
                after='Permiso retirado',
                field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}

    @classmethod
    def list(cls, page: int = 1, per_page: int = 20, filters: dict | None = None, sort: str | None = None):
        """Solo los permisos vigentes, y el total tambien.

        El CRUD generico no filtra la baja logica, asi que el gestor mostraba
        como concedidas filas que el guardia de peticion negaba -medido: 37 de
        506-. Un gestor que ensena un permiso que no funciona es peor que uno
        que no lo ensena: manda a buscar el problema en el rol, donde no hay
        nada que arreglar.

        Se filtra en SQL y no descartando despues lo que llego: con paginacion,
        recortar en memoria da un total que no coincide con lo que se ve, y en
        una pantalla de permisos ese tipo de mentira pequena cuesta una hora a
        quien la cree.
        """
        from sqlalchemy import func, select

        from app.models.session import transaction_context

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(cls.model).where(cls.model.deletion_date.is_(None))
            for clave, valor in filters.items():
                if not hasattr(cls.model, clave) or valor in (None, ''):
                    continue
                columna = getattr(cls.model, clave)
                if isinstance(valor, str):
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

