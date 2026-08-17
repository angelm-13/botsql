from app.models import SurveyMultipleAnswer
from app.services.base_service import CrudService


class SurveyMultipleAnswerService(CrudService):
    model = SurveyMultipleAnswer
    primary_key = 'id_survey_multiple_answer'
    entity_name = 'survey_multiple_answer'
