from sqlalchemy import or_
from app.models import EntityPermission, Permission, User
from app.models.session import transaction_context
from app.services.base_service import CrudService


class UserService(CrudService):
    model = User
    primary_key = 'id_user'
    entity_name = 'user'

    @classmethod
    def options(cls, *, capability: str | None = None) -> list[dict]:
        """Solo id+nombre, para selectores como "Responsable" en un vale de
        almacen o el lider de un proyecto. A proposito no exige el permiso
        de lectura completo de user (nombre, puesto, salario, RFC, etc.) --
        un rol que puede levantar un vale (ej. Almacenista) no
        necesariamente puede ver el catalogo de RH completo.

        Con `capability` solo salen quienes la tienen concedida en el Gestor de roles
        y permisos (p. ej. quien puede ser responsable de un vale).
        """
        with transaction_context() as session:
            consulta = (
                session.query(User.id_user, User.full_name, User.username,
                              Permission.permission_description)
                .outerjoin(Permission, Permission.id_permission == User.id_permission)
                .filter(User.deletion_date.is_(None))
                # Los compradores de la tienda en linea no son personal: su
                # username es su correo y no deben salir en un selector.
                .filter(or_(User.user_type.is_(None), User.user_type != 'web_shopper'))
            )
            if capability:
                concedida = session.query(EntityPermission.id_permission).filter(
                    EntityPermission.entity_name == capability,
                    EntityPermission.scope_read != 0,
                    EntityPermission.deletion_date.is_(None))
                consulta = consulta.filter(User.id_permission.in_(concedida))
            filas = consulta.order_by(User.full_name).all()
            return [
                {'id_user': fila[0], 'full_name': fila[1], 'username': fila[2],
                 'role': fila[3]}
                for fila in filas
            ]
