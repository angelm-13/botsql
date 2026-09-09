from app.models import User
from app.models.session import transaction_context
from app.services.base_service import CrudService


class UserService(CrudService):
    model = User
    primary_key = 'id_user'
    entity_name = 'user'

    @classmethod
    def options(cls) -> list[dict]:
        """Solo id+nombre, para selectores como "Responsable" en un vale de
        almacen o el lider de un proyecto. A proposito no exige el permiso
        de lectura completo de user (nombre, puesto, salario, RFC, etc.) --
        un rol que puede levantar un vale (ej. Almacenista) no
        necesariamente puede ver el catalogo de RH completo.
        """
        with transaction_context() as session:
            filas = (
                session.query(User.id_user, User.full_name, User.username)
                .filter(User.deletion_date.is_(None))
                .order_by(User.full_name)
                .all()
            )
            return [
                {'id_user': fila[0], 'full_name': fila[1], 'username': fila[2]}
                for fila in filas
            ]
