from app.models import NmTeamUser
from app.services.base_service import CrudService


class NmTeamUserService(CrudService):
    model = NmTeamUser
    primary_key = 'id_nm_team_user'
    entity_name = 'nm_team_user'
