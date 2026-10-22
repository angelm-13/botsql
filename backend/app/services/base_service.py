from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, Float, Integer, Numeric, SmallInteger, String, select, func
from sqlalchemy.exc import IntegrityError, StatementError
import bcrypt
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.validations.validator import validate_payload


class CrudService:
    model = None
    primary_key = 'id'
    entity_name = 'entity'

    @classmethod
    def _columns(cls):
        return {column.name: column for column in cls.model.__table__.columns}

    @staticmethod
    def _looks_like_bcrypt_hash(value) -> bool:
        text = str(value or '')
        return text.startswith(('$2a$', '$2b$', '$2y$')) and len(text) >= 55

    @classmethod
    def _hash_sensitive_payload_values(cls, payload: dict) -> None:
        # Seguridad: nunca guardar contraseñas nuevas en texto plano.
        # Se usa bcrypt, que ya es el mecanismo esperado por auth._verify_password
        # y por los seeds iniciales del sistema.
        for key in ('password', 'password_hash'):
            value = payload.get(key)
            if value in (None, ''):
                continue
            if cls._looks_like_bcrypt_hash(value):
                continue
            payload[key] = bcrypt.hashpw(str(value).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @classmethod
    def _user_required_error(cls, field: str) -> None:
        raise AppError(
            f'validations.user.{field}.required',
            status_code=400,
            meta={
                'entity': 'user',
                'field': field,
                'validation_type': 'required',
                'rule': 'value is not null and value != ""',
                'severity': 'error',
                'graphql_error_code': 'REQUIRED_FIELD',
            },
        )

    @staticmethod
    def _is_blank_value(value) -> bool:
        return value is None or (isinstance(value, str) and value.strip() == '')

    @classmethod
    def _prepare_user_credentials_for_write(cls, payload: dict, *, is_update: bool) -> dict:
        if cls.entity_name != 'user':
            return payload
        payload = dict(payload or {})
        if (not is_update) or ('username' in payload):
            if cls._is_blank_value(payload.get('username')):
                cls._user_required_error('username')
        if is_update:
            for key in ('password', 'password_hash'):
                if key in payload and cls._is_blank_value(payload.get(key)):
                    payload.pop(key, None)
            return payload
        password_value = payload.get('password', payload.get('password_hash'))
        if cls._is_blank_value(password_value):
            cls._user_required_error('password')
        return payload

    @classmethod
    def _coerce_payload(cls, payload: dict, partial: bool = False) -> dict:
        columns = cls._columns()
        clean_payload = {}
        for key, value in (payload or {}).items():
            column = columns.get(key)
            if column is None:
                continue
            if not partial and column.primary_key and column.autoincrement:
                continue
            clean_payload[key] = cls._coerce_value(column, value)
        cls._hash_sensitive_payload_values(clean_payload)
        cls._fill_system_defaults(clean_payload, partial=partial)
        validate_payload(cls.entity_name, clean_payload, partial=partial)
        cls._validate_required(clean_payload, partial=partial)
        return clean_payload

    @classmethod
    def _fill_system_defaults(cls, payload: dict, partial: bool = False) -> None:
        columns = cls._columns()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        create_fields = ('created_at', 'creation_date')
        update_fields = ('updated_at', 'last_update_date')

        if partial:
            # On update, keep audit/update timestamps current when the generated
            # schema exposes them. Do not depend on SQL defaults, because CSV
            # generated init.sql may define these columns as nullable.
            for name in update_fields:
                column = columns.get(name)
                if column is not None and name not in payload and isinstance(column.type, DateTime):
                    payload[name] = now
            return

        # On create, fill common audit timestamp columns when present and empty,
        # regardless of nullable/server_default metadata. This keeps frontend
        # tables from showing blank creation dates when init.sql has no DEFAULT.
        for name in create_fields + update_fields:
            column = columns.get(name)
            if column is not None and name not in payload and isinstance(column.type, DateTime):
                payload[name] = now


    @classmethod
    def _audit_enabled(cls) -> bool:
        return cls.entity_name != 'event_log'

    @staticmethod
    def _redact_audit_value(field_name: str, value):
        sensitive_tokens = ('password', 'pass', 'secret', 'token', 'otp', 'mfa', 'backup_code', 'iv', 'hash')
        normalized = str(field_name or '').lower()
        if any(token in normalized for token in sensitive_tokens):
            if value in (None, ''):
                return value
            return '[REDACTED]'
        return value

    @classmethod
    def _redact_audit_dict(cls, data: dict | None) -> dict:
        return {key: cls._redact_audit_value(key, value) for key, value in (data or {}).items()}

    @classmethod
    def _clean_audit_value(cls, field_name: str, value):
        if isinstance(value, dict):
            return cls._redact_audit_dict(value)
        if isinstance(value, list):
            return [cls._clean_audit_value(field_name, item) for item in value]
        return cls._redact_audit_value(field_name, value)

    @classmethod
    def _summarize_audit_record(cls, data: dict | None) -> str:
        data = data or {}
        system_fields = {
            'created_by', 'creation_date', 'last_update_date', 'deletion_date',
            'created_at', 'updated_at', 'deleted_at',
        }
        parts = []
        for key, value in data.items():
            if key in system_fields or value in (None, ''):
                continue
            clean_value = cls._clean_audit_value(key, value)
            if isinstance(clean_value, (dict, list)):
                continue
            parts.append(f'{key}: {clean_value}')
            if len(parts) >= 4:
                break
        if not parts:
            for key, value in data.items():
                if value in (None, ''):
                    continue
                clean_value = cls._clean_audit_value(key, value)
                if isinstance(clean_value, (dict, list)):
                    continue
                parts.append(f'{key}: {clean_value}')
                if len(parts) >= 4:
                    break
        return ', '.join(parts)

    @classmethod
    def _format_audit_create_after(cls, data: dict | None) -> str:
        summary = cls._summarize_audit_record(data)
        base = f'Nuevo registro creado en {cls.entity_name}'
        return f'{base}: {summary}' if summary else base

    @classmethod
    def _format_audit_delete_before(cls, data: dict | None) -> str:
        summary = cls._summarize_audit_record(data)
        base = f'Registro eliminado de {cls.entity_name}'
        return f'{base}: {summary}' if summary else base

    @classmethod
    def _write_event_log(cls, session, *, action: str, actor_id: int | None, before=None, after=None, field_name: str = '*') -> None:
        if not cls._audit_enabled():
            return
        try:
            from app.models import EventLog
        except Exception:
            return

        before_clean = cls._clean_audit_value(field_name, before if before is not None else '')
        after_clean = cls._clean_audit_value(field_name, after if after is not None else '')
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(EventLog(
            table_name=cls.entity_name,
            field_name=str(field_name or '*')[:50],
            action=action,
            before_value=before_clean,
            after_value=after_clean,
            created_by=actor_id or 1,
            creation_date=now,
            last_update_date=now,
        ))

    @classmethod
    def _audit_ignored_fields(cls) -> set[str]:
        # Campos tecnicos actualizados por el sistema. No representan una accion
        # funcional del usuario y ya quedan reflejados en las columnas de fecha
        # del propio registro de Event Log. Evitarlos reduce ruido en auditoria.
        return {
            'created_by',
            'created_at',
            'updated_at',
            'deleted_at',
            'creation_date',
            'last_update_date',
            'deletion_date',
        }

    @classmethod
    def _write_update_event_logs(cls, session, *, actor_id: int | None, before: dict, after: dict, payload: dict) -> None:
        if not cls._audit_enabled():
            return
        ignored_fields = cls._audit_ignored_fields()
        changed_fields = []
        for key in payload.keys():
            if key in ignored_fields:
                continue
            if before.get(key) != after.get(key):
                changed_fields.append(key)
        for key in changed_fields:
            cls._write_event_log(
                session,
                action='update',
                actor_id=actor_id,
                before=before.get(key),
                after=after.get(key),
                field_name=key,
            )

    @staticmethod
    def _coerce_value(column, value):
        if value == '':
            return None
        if value is None:
            return None
        try:
            if isinstance(column.type, (Integer, BigInteger, SmallInteger)):
                return int(value)
            if isinstance(column.type, Float):
                return float(value)
            if isinstance(column.type, Numeric):
                return Decimal(str(value))
            if isinstance(column.type, Boolean):
                if isinstance(value, bool):
                    return value
                normalized = str(value).strip().lower()
                if normalized in {'true', '1', 'yes', 'y', 'si', 'sí'}:
                    return True
                if normalized in {'false', '0', 'no', 'n'}:
                    return False
                raise ValueError(value)
            if isinstance(column.type, DateTime) and isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            if isinstance(column.type, Date) and isinstance(value, str):
                date_value = value.split('T', 1)[0].split(' ', 1)[0]
                return date.fromisoformat(date_value)
            length = getattr(column.type, 'length', None)
            if length and isinstance(value, str) and len(value) > int(length):
                raise AppError(
                    'errors.field_too_long',
                    status_code=400,
                    meta={
                        'field': column.name,
                        'max_length': int(length),
                        'actual_length': len(value),
                    },
                )
        except (TypeError, ValueError, InvalidOperation):
            raise AppError('errors.invalid_field', status_code=400, meta={'field': column.name})
        return value

    @classmethod
    def _validate_required(cls, payload: dict, partial: bool = False) -> None:
        missing = []
        for column in cls._columns().values():
            if column.nullable:
                continue
            if column.primary_key and (column.autoincrement or column.default is not None or column.server_default is not None):
                continue
            if column.default is not None or column.server_default is not None:
                continue
            if partial and column.name not in payload:
                continue
            if payload.get(column.name) is None:
                missing.append(column.name)
        if missing:
            raise AppError('errors.validation_failed', status_code=400, meta={'fields': missing})

    @classmethod
    def _database_constraint_detail(cls, error) -> str:
        return str(error.orig) if getattr(error, 'orig', None) else str(error)

    @classmethod
    def _raise_database_constraint_error(cls, error, *, action: str):
        detail = cls._database_constraint_detail(error)
        normalized = detail.lower()
        if action == 'delete' and 'violates foreign key constraint' in normalized and 'is still referenced from table' in normalized:
            raise AppError(
                'errors.delete_has_related_records',
                status_code=409,
                meta={'entity': cls.entity_name, 'action': action},
            )
        if cls.entity_name == 'user' and ('uq_user_username' in normalized or 'user_username_key' in normalized or ('duplicate key' in normalized and 'username' in normalized)):
            raise AppError('errors.username_already_exists', status_code=409)
        # El mensaje crudo de la base (tablas, valores, SQL) no sale al cliente: va al log.
        # Solo el nombre de la restriccion, que algunas pantallas usan para explicar el error.
        import logging
        import re
        logging.getLogger(__name__).warning("restriccion de base de datos: %s", detail)
        nombre = re.search(r'constraint "?([A-Za-z0-9_]+)"?', detail)
        raise AppError('errors.database_constraint', status_code=400,
                       meta={'detail': nombre.group(1) if nombre else None})

    @classmethod
    def _busqueda_libre(cls, texto, campos=None):
        """Una sola caja de texto que busca por lo que sea.

        Por que hace falta
        ------------------
        El filtro por campo ya existia -- `?descripcion=taladro` hace su
        ILIKE -- pero obliga a saber EN QUE campo esta lo que se busca. Y el
        buscador de las pantallas filtraba en el CLIENTE, sobre la pagina ya
        cargada: con 2 221 productos en 56 paginas, teclear un nombre estando en
        la pagina 1 no encuentra el que vive en la 34. Que es exactamente el
        caso de "no se que nombre tiene el producto 8580".

        Que compara
        -----------
        Las columnas de TEXTO con ILIKE, y las numericas solo si lo escrito es
        un numero entero -- para que "8580" encuentre el id 8580 --.

        Fechas y booleanos quedan fuera: un ILIKE contra una fecha no significa
        nada y en Postgres revienta por tipo. Los `Enum` tambien, por el mismo
        motivo por el que el filtro por campo ya los trataba aparte.
        """
        from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, Numeric, or_

        limpio = str(texto or "").strip()
        if not limpio:
            return None

        try:
            como_numero = int(limpio)
        except (TypeError, ValueError):
            como_numero = None

        condiciones = []
        for nombre, columna in cls._columns().items():
            tipo = columna.type
            if isinstance(tipo, (Enum, Date, DateTime, Boolean)):
                continue
            # La caja de busqueda no es un oraculo sobre secretos: sin esto
            # `?q=$2b$12$` encontraba usuarios por el prefijo de su hash.
            if "password" in nombre.lower():
                continue
            # `campos`: solo lo que el actor puede ver; sin esto la busqueda era
            # un oraculo sobre columnas ocultas (RFC, SSN, salario...).
            if campos is not None and nombre not in campos:
                continue
            atributo = getattr(cls.model, nombre, None)
            if atributo is None:
                continue
            if isinstance(tipo, (Integer, Numeric)):
                if como_numero is not None:
                    condiciones.append(atributo == como_numero)
            else:
                condiciones.append(atributo.ilike("%" + limpio + "%"))
        return or_(*condiciones) if condiciones else None

    # Si el listado esconde lo que esta de baja. Como borrar es una baja logica
    # (`deletion_date`), lo borrado no debe volver a salir en pantalla.
    solo_vigentes = True

    @classmethod
    def _tiene_baja_logica(cls) -> bool:
        return 'deletion_date' in cls._columns()

    @classmethod
    def _esta_de_baja(cls, item) -> bool:
        return cls._tiene_baja_logica() and getattr(item, 'deletion_date', None) is not None

    @classmethod
    def list(cls, page: int = 1, per_page: int = 20, filters: dict | None = None,
             sort: str | None = None, q: str | None = None, search_fields=None):
        filters = filters or {}
        # Sin tope, per_page=100000 trae la tabla entera; el techo deja pasar a
        # los selectores que cargan catalogos completos (per_page=5000).
        page = max(1, int(page))
        per_page = min(max(1, int(per_page)), 5000)
        with transaction_context() as session:
            stmt = select(cls.model)
            if cls.solo_vigentes and hasattr(cls.model, 'deletion_date'):
                # En SQL y no descartando despues lo que llego: con paginacion,
                # recortar en memoria da un total que no coincide con lo que se
                # ve, y en una pantalla de permisos esa mentira pequena cuesta
                # una hora a quien la cree.
                stmt = stmt.where(cls.model.deletion_date.is_(None))
            busqueda = cls._busqueda_libre(q, search_fields)
            if busqueda is not None:
                stmt = stmt.where(busqueda)
            for key, value in filters.items():
                model_column = cls._columns().get(key)
                # Solo columnas reales: un atributo cualquiera del modelo
                # (metadata, registry...) no es un filtro valido.
                if model_column is None or value in (None, '') or 'password' in key.lower():
                    continue
                column = getattr(cls.model, key)
                # Buscar por coincidencia parcial solo tiene sentido en texto:
                # `id_customer_supplier ILIKE '%10%'` revienta en Postgres.
                if (isinstance(value, str) and isinstance(model_column.type, String)
                        and not isinstance(model_column.type, Enum)):
                    stmt = stmt.where(column.ilike(f'%{value}%'))
                else:
                    stmt = stmt.where(column == value)
            if sort and sort.lstrip('-') in cls._columns():
                col = getattr(cls.model, sort.lstrip('-'))
                stmt = stmt.order_by(col.desc() if sort.startswith('-') else col.asc())
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            items = session.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
            return {'items': [item.serialize() for item in items], 'total': total, 'page': page, 'per_page': per_page, 'pages': (total + per_page - 1) // per_page}

    @classmethod
    def get(cls, item_id):
        with transaction_context() as session:
            item = session.get(cls.model, item_id)
            if not item or (cls.solo_vigentes and cls._esta_de_baja(item)):
                raise AppError('errors.resource_not_found', status_code=404)
            return item.serialize()

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        if user_id and 'created_by' not in payload:
            payload['created_by'] = user_id
        payload = cls._prepare_user_credentials_for_write(payload, is_update=False)
        payload = cls._coerce_payload(payload)
        try:
            with transaction_context() as session:
                item = cls.model(**payload)
                session.add(item)
                session.flush()
                serialized = item.serialize()
                cls._write_event_log(
                    session,
                    action='create',
                    actor_id=user_id,
                    before='',
                    after=cls._format_audit_create_after(serialized),
                    field_name='*',
                )
                return serialized
        except (IntegrityError, StatementError) as error:
            cls._raise_database_constraint_error(error, action='create')

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = cls._prepare_user_credentials_for_write(dict(payload or {}), is_update=True)
        payload = cls._coerce_payload(payload, partial=True)
        try:
            with transaction_context() as session:
                item = session.get(cls.model, item_id)
                if not item or cls._esta_de_baja(item):
                    raise AppError('errors.resource_not_found', status_code=404)
                before = item.serialize()
                llaves = {c.name for c in cls.model.__table__.primary_key.columns}
                for key, value in payload.items():
                    # La llave primaria no se reescribe por un PUT.
                    if hasattr(item, key) and key not in llaves:
                        setattr(item, key, value)
                session.flush()
                after = item.serialize()
                cls._write_update_event_logs(
                    session,
                    actor_id=user_id,
                    before=before,
                    after=after,
                    payload=payload,
                )
                return after
        except (IntegrityError, StatementError) as error:
            cls._raise_database_constraint_error(error, action='update')

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        try:
            with transaction_context() as session:
                item = session.get(cls.model, item_id)
                if not item or cls._esta_de_baja(item):
                    raise AppError('errors.resource_not_found', status_code=404)
                before = item.serialize()
                if cls._tiene_baja_logica():
                    # Baja logica: la fila se queda en la base (con su historia y
                    # lo que la referencia) y solo deja de salir en pantalla.
                    item.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
                else:
                    session.delete(item)
                cls._write_event_log(
                    session,
                    action='delete',
                    actor_id=user_id,
                    before=cls._format_audit_delete_before(before),
                    after='Registro eliminado',
                    field_name='*',
                )
                session.flush()
                return {'message_key': 'success.deleted'}
        except (IntegrityError, StatementError) as error:
            cls._raise_database_constraint_error(error, action='delete')
