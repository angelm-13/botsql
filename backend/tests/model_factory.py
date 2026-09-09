from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, JSON, LargeBinary, Numeric, String


FIXED_DATE = date(2026, 1, 15)
FIXED_DATETIME = datetime(2026, 1, 15, 12, 0, 0)


def _value_for_type(column_type, value=None):
    if isinstance(column_type, DateTime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                pass
        return FIXED_DATETIME
    if isinstance(column_type, Date):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.split('T', 1)[0])
            except ValueError:
                pass
        return FIXED_DATE
    if isinstance(column_type, Boolean):
        return value if isinstance(value, bool) else True
    if isinstance(column_type, Integer):
        try:
            return int(value) if value is not None else 1
        except (TypeError, ValueError):
            return 1
    if isinstance(column_type, Numeric):
        try:
            return Decimal(str(value)) if value is not None else Decimal('1')
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('1')
    if isinstance(column_type, Enum):
        return value if value in column_type.enums else column_type.enums[0]
    if isinstance(column_type, LargeBinary):
        if isinstance(value, bytes):
            return value
        return str(value or 'test').encode('utf-8')
    if isinstance(column_type, JSON):
        if not isinstance(value, str):
            return value if value is not None else {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    if isinstance(column_type, String):
        text = str(value if value is not None else 'test')
        return text[:column_type.length] if column_type.length else text
    return value if value is not None else 1


def build_model(model_class, **overrides):
    return model_class(**build_model_values(model_class, overrides))


def build_model_values(model_class, overrides=None):
    overrides = dict(overrides or {})
    values = {}
    for column in model_class.__table__.columns:
        if column.primary_key and column.autoincrement:
            continue
        supplied = column.name in overrides
        if not supplied and (column.nullable or column.default is not None or column.server_default is not None):
            continue
        values[column.name] = _value_for_type(column.type, overrides.get(column.name))
    return values


def build_payload(service_class, overrides=None, **extra_overrides):
    values = dict(overrides or {})
    values.update(extra_overrides)
    return build_model_values(service_class.model, values)

def sembrar_actor(db, *, id_proyect, id_status, ids=(1,)):
    """El usuario que firma las pruebas: de verdad, y no solo de nombre.

    Por que hace falta
    ------------------
    Las fijaciones escriben `created_by=1` y `id_user=1` por todas partes sin
    que exista ningun usuario 1. Funciona porque SQLite no aplica las llaves
    ajenas -`PRAGMA foreign_keys` viene apagado-, asi que un numero que no
    apunta a nada se guarda igual.

    Deja de funcionar en cuanto un servicio COMPRUEBA lo que la base ya deberia
    exigir. `inventory_asset.id_holder` y `incident.id_user` -el responsable de
    una pieza y el de un vale- ahora se comprueban, porque en produccion la
    llave ajena existe y un identificador inventado reventaba en el COMMIT como
    un 500 en lugar de un 404.

    Sobre el ciclo
    --------------
    `user` -> `permission` -> `user` es un ciclo real, el mismo que obligo a
    declarar esas llaves DEFERRABLE en el esquema. Aqui se resuelve escribiendo
    el permiso primero con `authorized_by` apuntando al usuario que todavia no
    existe, que es exactamente lo que SQLite permite y Postgres solo acepta con
    la comprobacion diferida. Sembrar esto en la base de pruebas de Postgres es
    parte de esa migracion, no de aqui.
    """
    from app.models.department import Department
    from app.models.level import Level
    from app.models.permission import Permission
    from app.models.subdepartment import Subdepartment
    from app.models.user import User

    primero = ids[0]
    db.add_all([
        Department(id_department=1, department_description='General', created_by=primero),
        Level(id_level=1, level_description='Base', created_by=primero),
    ])
    db.flush()
    db.add(Subdepartment(id_subdepartment=1, subdepartment_description='General',
                         id_department=1, created_by=primero))
    db.flush()
    db.add(Permission(id_permission=1, permission_description='Pruebas',
                      authorized_by=primero, id_department=1, id_subdepartment=1,
                      id_level=1, created_by=primero))
    db.flush()
    # Uno por cada identificador que las pruebas usen: el que firma las
    # operaciones y los que reciben la herramienta. Un responsable que no existe
    # es la pieza prestada a nadie.
    db.add_all([
        User(id_user=uno, full_name='Usuario de pruebas %d' % uno,
             username='pruebas%d' % uno, id_permission=1, id_proyect=id_proyect,
             id_status=id_status, supervisor=primero, created_by=primero)
        for uno in ids
    ])
    db.flush()
    return primero
