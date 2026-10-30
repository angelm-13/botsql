from app.models import NmFieldPermission
from app.services.base_service import CrudService


class NmFieldPermissionService(CrudService):
    model = NmFieldPermission
    primary_key = 'id_nm_field_permission'
    entity_name = 'nm_field_permission'

    # De estas filas salen los atributos que una pantalla pinta. Una de baja
    # significa que el permiso se retiro, asi que devolverla vuelve a mostrar
    # el campo: el listado la escondia y la pantalla la creia concedida.
    solo_vigentes = True

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        """Retirar un permiso de campo lo marca de baja; no borra la fila.

        Mismo motivo que `EntityPermissionService.delete`: con borrado fisico
        una fila ausente significa a la vez "nunca se sembro" y "el
        administrador la retiro", y el INSERT de reposicion que traen las
        migraciones -que solo mira si hay una VIGENTE- la devolveria en el
        siguiente despliegue. Con la baja queda constancia, y el trigger
        `trg_no_resucitar` la respeta.
        """
        from datetime import datetime, timezone

        from app.models.session import transaction_context
        from app.utils.errors import AppError

        with transaction_context() as session:
            item = session.get(cls.model, item_id)
            if not item:
                raise AppError('errors.resource_not_found', status_code=404)
            if item.deletion_date is not None:
                return {'message_key': 'success.deleted'}
            before = item.serialize()
            item.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
            cls._write_event_log(
                session,
                action='delete',
                actor_id=user_id,
                before=cls._format_audit_delete_before(before),
                after='Permiso de campo retirado',
                field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}
