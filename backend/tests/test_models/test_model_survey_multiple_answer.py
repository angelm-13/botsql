from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.survey_multiple_answer import SurveyMultipleAnswer


class TestSurveyMultipleAnswerModel(BackendTestCase):
    def test_create_serialize_summary_delete_survey_multiple_answer(self):
        with transaction_context() as session:
            item = SurveyMultipleAnswer(
            survey_answer_description='test_survey_answer_description',
            score=1,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
