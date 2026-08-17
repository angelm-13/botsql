from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.nm_survey_user import NmSurveyUser


class TestNmSurveyUserModel(BackendTestCase):
    def test_create_serialize_summary_delete_nm_survey_user(self):
        with transaction_context() as session:
            item = NmSurveyUser(
            nm_survey_user_description='test_nm_survey_user_description',
            score=1,
            status=1,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
