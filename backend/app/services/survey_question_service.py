from app.models import SurveyQuestion
from app.services.base_service import CrudService


class SurveyQuestionService(CrudService):
    model = SurveyQuestion
    primary_key = 'id_survey_question'
    entity_name = 'survey_question'
