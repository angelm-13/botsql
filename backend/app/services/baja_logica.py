"""Baja logica para los servicios de CRUD que la piden (hoy `team` y `nm_team_user`).

El `delete` del CRUD generico (`CrudService.delete`) borra la fila. Aqui no: una baja pone
`deletion_date` y la fila se queda. Es opt-in por servicio -- se mezcla ANTES de `CrudService` en las
bases -- y el borrado del resto de las entidades no cambia.

Por que, para equipos y membresias: los KPIs de asistencia atribuyen cada marca al equipo que la persona
tenia EN ESE MOMENTO (`creation_date <= instante < deletion_date` de la membresia). Con borrado fisico la
persona que se movio de un equipo a otro dejaria sin historia a las marcas anteriores; con la baja, el
periodo viejo queda como una fila mas. Ver `docs/mapa-entidades-kpis.md` §8.

* `solo_vigentes`: los listados (`GET /team/`, `GET /nm_team_user/`) no ensenan lo que esta de baja.
* `get` y `update` de una fila de baja dan 404: ya no rige, igual que si no existiera.
* `delete` de una fila ya de baja no la vuelve a fechar (se perderia cuando se retiro de verdad).
"""

from __future__ import annotations

from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.tiempo import ahora_utc


class BajaLogicaMixin:
    solo_vigentes = True

    @classmethod
    def _vigente_o_404(cls, session, item_id):
        item = session.get(cls.model, item_id)
        if item is None or item.deletion_date is not None:
            raise AppError('errors.resource_not_found', status_code=404)
        return item

    @classmethod
    def get(cls, item_id):
        with transaction_context() as session:
            return cls._vigente_o_404(session, item_id).serialize()

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        with transaction_context() as session:
            cls._vigente_o_404(session, item_id)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def _al_dar_de_baja(cls, session, item, ahora, user_id) -> None:
        """Gancho para lo que tiene que caer junto con la fila, en la misma transaccion y con el mismo instante."""

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        with transaction_context() as session:
            item = session.get(cls.model, item_id)
            if item is None:
                raise AppError('errors.resource_not_found', status_code=404)
            if item.deletion_date is not None:
                return {'message_key': 'success.deleted'}
            before = item.serialize()
            ahora = ahora_utc()
            item.deletion_date = ahora
            cls._al_dar_de_baja(session, item, ahora, user_id)
            cls._write_event_log(
                session,
                action='delete',
                actor_id=user_id,
                before=cls._format_audit_delete_before(before),
                after='Registro dado de baja',
                field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}
