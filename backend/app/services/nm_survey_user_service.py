from app.models import NmSurveyUser
from app.services.base_service import CrudService


class NmSurveyUserService(CrudService):
    model = NmSurveyUser
    primary_key = 'id_nm_survey_user'
    entity_name = 'nm_survey_user'
