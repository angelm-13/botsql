from app.models import NmTeamUser, Team
from app.models.session import transaction_context
from app.services.baja_logica import BajaLogicaMixin
from app.services.base_service import CrudService
from app.services.nm_team_user_service import NmTeamUserService
from app.utils.errors import AppError


class TeamService(BajaLogicaMixin, CrudService):
    """Un equipo no se borra: se da de baja, y con el sus membresias vigentes.

    El nombre es unico entre los equipos VIGENTES (sin importar mayusculas ni espacios de los lados); el de
    uno dado de baja se puede volver a usar. Renombrar conserva el `id_team`, asi que las membresias y los
    KPIs ya guardados siguen siendo del mismo equipo.
    """

    model = Team
    primary_key = 'id_team'
    entity_name = 'team'

    @staticmethod
    def _limpio(payload: dict) -> dict:
        payload = dict(payload or {})
        if isinstance(payload.get('team_description'), str):
            payload['team_description'] = payload['team_description'].strip()
        return payload

    @classmethod
    def _rechazar_nombre_repetido(cls, nombre, item_id=None) -> None:
        buscado = str(nombre or '').strip().casefold()
        if not buscado:
            return
        with transaction_context() as session:
            vigentes = session.query(Team.id_team, Team.team_description).filter(Team.deletion_date.is_(None)).all()
        propio = int(item_id) if str(item_id).isdigit() else None
        for id_team, descripcion in vigentes:
            if propio is not None and int(id_team) == propio:
                continue
            if str(descripcion or '').strip().casefold() == buscado:
                raise AppError('errors.team_name_duplicate', status_code=409, meta={'field': 'team_description'})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = cls._limpio(payload)
        cls._rechazar_nombre_repetido(payload.get('team_description'))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = cls._limpio(payload)
        if 'team_description' in payload:
            cls._rechazar_nombre_repetido(payload['team_description'], item_id)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def _al_dar_de_baja(cls, session, item, ahora, user_id) -> None:
        """Las membresias vigentes caen con el equipo, en el mismo instante: quienes las tenian pasan a "Sin equipo"."""
        membresias = session.query(NmTeamUser).filter(
            NmTeamUser.id_team == item.id_team,
            NmTeamUser.deletion_date.is_(None),
        ).all()
        for membresia in membresias:
            antes = membresia.serialize()
            membresia.deletion_date = ahora
            NmTeamUserService._write_event_log(
                session,
                action='delete',
                actor_id=user_id,
                before=NmTeamUserService._format_audit_delete_before(antes),
                after='Registro dado de baja con su equipo',
                field_name='*',
            )
