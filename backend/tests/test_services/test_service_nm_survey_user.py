from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.nm_survey_user_service import NmSurveyUserService


class TestNmSurveyUserService(BackendTestCase):
    def test_crud_service_nm_survey_user(self):
        created = NmSurveyUserService.create({'nm_survey_user_description': 'test_nm_survey_user_description', 'score': 1, 'status': 1, 'created_by': 1})
        self.assertIsNotNone(created)
        page = NmSurveyUserService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
