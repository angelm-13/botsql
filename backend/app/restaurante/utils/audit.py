"""
Bitacora de auditoria: registra quien hizo que cambio administrativo y
cuando (ver AuditLog en models/entities.py). No hay un "current_user"
reutilizable en el proyecto (roles_required solo valida el claim 'role'
del JWT, ver utils/security.py), asi que aqui se busca el User igual que
ya lo hacen otras rutas (por ejemplo auth.py:/me).

log_action() solo agrega el registro a la sesion -- no hace commit por su
cuenta, para que quede en la MISMA transaccion que el cambio que esta
auditando (si algo mas falla despues y se hace rollback, el log tampoco
se guarda a medias).
"""
from flask_jwt_extended import get_jwt_identity
from app.extensions import db
from app.restaurante.models import User, AuditLog


def log_action(action, entity_type, entity_id, description):
    user = User.query.get(int(get_jwt_identity()))
    db.session.add(AuditLog(
        actor_user_id=user.id if user else None,
        actor_username=user.username if user else 'desconocido',
        actor_role=user.role if user else 'desconocido',
        action=action, entity_type=entity_type, entity_id=entity_id, description=description,
    ))
