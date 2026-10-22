from app.models import NmTeamUser, Team
from app.models.session import transaction_context
from app.services.baja_logica import BajaLogicaMixin
from app.services.base_service import CrudService
from app.utils.errors import AppError


class NmTeamUserService(BajaLogicaMixin, CrudService):
    """Una membresia es un PERIODO de una persona en un equipo.

    Quitar a alguien de un equipo la da de baja (`deletion_date`) y no la borra; volver a agregarlo despues
    crea una membresia nueva, y la anterior queda como historia. Asi cada marca de checada se atribuye al
    equipo que la persona tenia entonces. Lo que no puede haber son dos membresias VIGENTES iguales
    (`uq_nm_team_user_vigente`).
    """

    model = NmTeamUser
    primary_key = 'id_nm_team_user'
    entity_name = 'nm_team_user'

    @classmethod
    def _validar_alta(cls, id_team: int, id_user: int) -> None:
        with transaction_context() as session:
            equipo = session.get(Team, id_team)
            if equipo is None or equipo.deletion_date is not None:
                raise AppError('errors.team_not_available', status_code=400, meta={'field': 'id_team'})
            ya_esta = session.query(NmTeamUser.id_nm_team_user).filter(
                NmTeamUser.id_team == id_team,
                NmTeamUser.id_user == id_user,
                NmTeamUser.deletion_date.is_(None),
            ).first()
            if ya_esta:
                raise AppError('errors.team_member_duplicate', status_code=409, meta={'field': 'id_user'})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        try:
            id_team, id_user = int(payload.get('id_team')), int(payload.get('id_user'))
        except (TypeError, ValueError):
            pass    # sin equipo o persona validos, la validacion de siempre lo rechaza con su 400
        else:
            cls._validar_alta(id_team, id_user)
        return super().create(payload, user_id=user_id)
