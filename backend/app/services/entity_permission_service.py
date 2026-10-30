from app.models import EntityPermission
from app.services.base_service import CrudService


class EntityPermissionService(CrudService):
    model = EntityPermission
    primary_key = 'id_entity_permission'
    entity_name = 'entity_permission'

    # --- que alcance admite cada fila --------------------------------------
    #
    # Propios y Mis grupos solo significan algo para un registro con dueno. Una
    # capacidad (autorizar un vale, recibir una compra...) no lo tiene, y el
    # Gestor de Administracion tampoco puede acotarse: es la unica puerta para
    # arreglar un permiso mal puesto.

    ENTIDADES_DE_ADMINISTRACION = frozenset({
        'permission', 'entity_permission', 'nm_field_permission', 'field',
        'team', 'nm_team_user',
    })

    @classmethod
    def _validar_alcance(cls, entity_name, id_permission, payload: dict, actuales: dict | None = None):
        from app.utils.errors import AppError
        from app.utils.scope import SCOPE_ALL, SCOPE_NONE, capacidad_solo_todos

        columnas = ('scope_create', 'scope_read', 'scope_update', 'scope_delete')
        # Solo cuenta lo que CAMBIA: un 1 o 2 que ya estaba guardado desde antes
        # de esta regla no debe impedir guardar el resto del rol.
        actuales = actuales or {}
        valores = {
            c: int(payload[c]) for c in columnas
            if payload.get(c) is not None and int(payload[c]) != int(actuales.get(c) or 0)
        }
        solo_todos = capacidad_solo_todos(entity_name) or entity_name in cls.ENTIDADES_DE_ADMINISTRACION
        if solo_todos and any(v not in (SCOPE_NONE, SCOPE_ALL) for v in valores.values()):
            raise AppError('errors.permission_scope_only_all', 400,
                           {'entity': entity_name})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar_alcance(payload.get('entity_name'), payload.get('id_permission'), payload)
        # Quitar un permiso es una baja logica (ver `delete`) y la tabla es
        # UNIQUE (id_permission, entity_name): volver a concederlo con un INSERT
        # choca con la fila de baja. Se reactiva esa misma fila y se le aplican
        # los alcances nuevos, en vez de crear otra.
        from sqlalchemy import select

        from app.models.session import transaction_context

        with transaction_context() as session:
            baja = session.scalar(
                select(cls.model).where(
                    cls.model.id_permission == payload.get('id_permission'),
                    cls.model.entity_name == payload.get('entity_name'),
                    cls.model.deletion_date.is_not(None),
                )
            )
            id_baja = baja.id_entity_permission if baja is not None else None
            if baja is not None:
                baja.deletion_date = None
                # Una fila reactivada arranca sin alcance: lo que cuenta es lo
                # que llega en el payload, no lo que tenia al darse de baja.
                for c in ('scope_create', 'scope_read', 'scope_update', 'scope_delete'):
                    setattr(baja, c, 0)
        if id_baja is not None:
            return cls.update(id_baja, payload, user_id=user_id)
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        from app.models.session import transaction_context
        from app.utils.errors import AppError

        with transaction_context() as session:
            fila = session.get(cls.model, item_id)
            if fila is None:
                raise AppError('errors.resource_not_found', 404)
            entidad = payload.get('entity_name') or fila.entity_name
            cls._validar_alcance(
                entidad, fila.id_permission, payload,
                actuales={c: getattr(fila, c) for c in ('scope_create', 'scope_read', 'scope_update', 'scope_delete')},
            )
            # Anti-bloqueo: quien administra no se quita a si mismo el Gestor.
            if entidad == 'entity_permission' and user_id is not None:
                from app.models.user import User
                actor = session.get(User, int(user_id))
                propio = actor is not None and int(getattr(actor, 'id_permission', 0) or 0) == int(fila.id_permission)
                if propio and any(
                    payload.get(c) is not None and int(payload[c]) == 0
                    for c in ('scope_read', 'scope_update')
                ):
                    raise AppError('errors.permission_manager_lockout', 409)
        return super().update(item_id, payload, user_id=user_id)

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
    def list(cls, page: int = 1, per_page: int = 20, filters: dict | None = None,
             sort: str | None = None, q: str | None = None):
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
            # La busqueda libre, sin perder el filtro de baja logica de arriba.
            busqueda = cls._busqueda_libre(q)
            if busqueda is not None:
                stmt = stmt.where(busqueda)
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

