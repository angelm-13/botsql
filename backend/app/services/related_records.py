"""Que registros impiden borrar a otro.

Cuando un borrado fisico choca con una llave foranea, el cliente solo sabia que "esta relacionado con
otros registros". Aqui se averigua con cuales: por cada tabla que apunta a la fila, cuantas filas la
referencian. El cliente pone el nombre legible de cada tabla (`related_tables.<tabla>` en el i18n del
frontend); el backend solo manda el nombre tecnico y los conteos.

Las filas dadas de baja (`deletion_date`) se cuentan aparte: siguen en la base y la llave foranea las
sigue viendo, asi que bloquean igual que una vigente, pero quien borra no las ve en pantalla y hay que
decirselo o parece que el sistema se contradice.

Se recorren los modelos (`Base.metadata`), no el catalogo de Postgres: funciona igual en las pruebas con
SQLite y no necesita permisos sobre `pg_constraint`.
"""

from __future__ import annotations

import logging

from sqlalchemy import Integer, func, or_, select

from app.models.base import Base
from app.models.session import transaction_context
from app.utils.errors import AppError

LOGGER = logging.getLogger(__name__)


def delete_has_related_records_error(entity: str, table_name: str, pk_value) -> AppError:
    """El 409 de "no se puede borrar" con el detalle de que lo impide en `meta.related`."""
    related = related_records(table_name, pk_value) if pk_value is not None else []
    return AppError(
        'errors.delete_has_related_records',
        status_code=409,
        meta={'entity': entity, 'action': 'delete', 'related': related},
    )


def related_records(table_name: str, pk_value) -> list[dict]:
    """[{'table', 'count', 'deleted_count'}] de las tablas con filas que referencian `pk_value`.

    Nunca lanza: si algo falla devuelve [] para no tapar el 409 que se esta explicando.
    """
    try:
        return _related_records(table_name, pk_value)
    except Exception:  # noqa: BLE001 - es solo un detalle del mensaje de error
        LOGGER.warning("no se pudieron listar los registros relacionados de %s", table_name, exc_info=True)
        return []


def _related_records(table_name: str, pk_value) -> list[dict]:
    target = Base.metadata.tables.get(table_name)
    if target is None or len(target.primary_key.columns) != 1:
        return []
    pk_column = next(iter(target.primary_key.columns))
    if isinstance(pk_column.type, Integer):
        pk_value = int(pk_value)

    found = []
    with transaction_context() as session:
        # `tables`, no `sorted_tables`: el orden no importa y este avisa de ciclos entre tablas.
        for table in Base.metadata.tables.values():
            columns = [
                fk.parent for fk in table.foreign_keys
                if fk.column.table is target and fk.column is pk_column
            ]
            if not columns:
                continue
            match = or_(*[column == pk_value for column in columns])
            if table is target:
                # Una fila que se apunta a si misma (creada_por ella misma) no es lo que impide borrarla.
                match = match & (pk_column != pk_value)
            total = session.execute(select(func.count()).select_from(table).where(match)).scalar() or 0
            if not total:
                continue
            deleted = 0
            if 'deletion_date' in table.c:
                deleted = session.execute(
                    select(func.count()).select_from(table)
                    .where(match, table.c.deletion_date.isnot(None))
                ).scalar() or 0
            found.append({'table': table.name, 'count': int(total), 'deleted_count': int(deleted)})
    found.sort(key=lambda row: (-row['count'], row['table']))
    return found
