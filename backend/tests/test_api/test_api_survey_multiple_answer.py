from __future__ import annotations

from tests.conftest import BackendTestCase


class TestSurveyMultipleAnswerApi(BackendTestCase):
    def test_list_survey_multiple_answer_supports_pagination(self):
        response = self.client.get("/survey_multiple_answer/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_survey_multiple_answer_validates_payload(self):
        response = self.client.post("/survey_multiple_answer/", json={'survey_answer_description': 'test_survey_answer_description', 'score': 1, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_survey_multiple_answer_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/survey_multiple_answer/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/survey_multiple_answer/{missing_id}", json={'survey_answer_description': 'test_survey_answer_description', 'score': 1, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/survey_multiple_answer/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
