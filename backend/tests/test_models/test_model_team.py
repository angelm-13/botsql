from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.team import Team


class TestTeamModel(BackendTestCase):
    def test_create_serialize_summary_delete_team(self):
        with transaction_context() as session:
            item = build_model(Team,
            team_description='test description',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            self.assertEqual(data['team_description'], 'test description')
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
