from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.survey_question_service import SurveyQuestionService


class TestSurveyQuestionService(BackendTestCase):
    def test_crud_service_survey_question(self):
        created = SurveyQuestionService.create({'question': 'test_question', 'question_type': 'single_option', 'owner': 1, 'created_by': 1})
        self.assertIsNotNone(created)
        page = SurveyQuestionService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
