from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.survey_multiple_answer_service import SurveyMultipleAnswerService


class TestSurveyMultipleAnswerService(BackendTestCase):
    def test_crud_service_survey_multiple_answer(self):
        created = SurveyMultipleAnswerService.create({'survey_answer_description': 'test_survey_answer_description', 'score': 1, 'created_by': 1})
        self.assertIsNotNone(created)
        page = SurveyMultipleAnswerService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
