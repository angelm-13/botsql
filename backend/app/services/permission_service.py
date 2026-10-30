from datetime import datetime, timezone

from app.models import Permission
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class PermissionService(CrudService):
    model = Permission
    primary_key = 'id_permission'
    entity_name = 'permission'

    # Un perfil de baja ya no concede nada: sus filas de `entity_permission` se
    # retiran con el, y todo lo que resuelve permisos -- el login, el menu, el
    # guardia de peticion -- pregunta por `deletion_date IS NULL`. Ofrecerlo en
    # el selector del gestor es ofrecer un rol que no da acceso a nada.
    #
    # Medido despues de retirar los cinco roles redundantes: el selector seguia
    # listando 'Jefe de taller', 'Mesero', 'Cocina', 'Caja Restaurante' y
    # 'Admin Restaurante', y asignarlos habria dejado al usuario sin permisos
    # sin decirlo en ningun sitio.
    solo_vigentes = True

    @classmethod
    def options(cls) -> list[dict]:
        """Solo id+nombre de los roles vigentes, para el selector "Rol/perfil"
        del alta de usuario. A proposito no exige el permiso de lectura de
        `permission`: quien da de alta usuarios elige un rol sin administrar el
        catalogo de roles.
        """
        with transaction_context() as session:
            filas = (
                session.query(Permission.id_permission, Permission.permission_description)
                .filter(Permission.deletion_date.is_(None))
                .order_by(Permission.permission_description)
                .all()
            )
            return [
                {'id_permission': fila[0], 'permission_description': fila[1]}
                for fila in filas
            ]

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        """Retirar un perfil lo marca de baja; no borra la fila.

        Mismo motivo que en `entity_permission`, mas uno propio de esta tabla:
        `user.id_permission` apunta aqui. Con el borrado fisico del CRUD
        generico, retirar un perfil que alguien todavia tiene asignado falla con
        un error de llave foranea -- y el administrador se queda sin forma de
        retirarlo salvo reasignando antes a cada usuario, uno por uno, sin que
        la pantalla le diga que ese es el problema.

        Marcandolo de baja, el perfil deja de conceder y deja de ofrecerse de
        inmediato, los usuarios que lo tenian siguen existiendo -- sin permisos,
        que es lo correcto: el perfil se retiro -- y queda el rastro de quien lo
        retiro y cuando.
        """
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
                after='Perfil retirado',
                field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}
