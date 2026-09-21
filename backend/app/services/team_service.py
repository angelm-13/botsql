from app.models import Team
from app.services.base_service import CrudService


class TeamService(CrudService):
    model = Team
    primary_key = 'id_team'
    entity_name = 'team'
