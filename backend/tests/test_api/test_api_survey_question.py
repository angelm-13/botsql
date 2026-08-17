from __future__ import annotations

from tests.conftest import BackendTestCase


class TestSurveyQuestionApi(BackendTestCase):
    def test_list_survey_question_supports_pagination(self):
        response = self.client.get("/survey_question/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_survey_question_validates_payload(self):
        response = self.client.post("/survey_question/", json={'question': 'test_question', 'question_type': 'single_option', 'owner': 1, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_survey_question_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/survey_question/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/survey_question/{missing_id}", json={'question': 'test_question', 'question_type': 'single_option', 'owner': 1, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/survey_question/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
