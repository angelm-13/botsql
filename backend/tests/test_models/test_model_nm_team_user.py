from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.team import Team
from app.models.nm_team_user import NmTeamUser


class TestNmTeamUserModel(BackendTestCase):
    def test_create_serialize_summary_delete_nm_team_user(self):
        with transaction_context() as session:
            team = build_model(Team, team_description='Equipo de prueba', created_by=1)
            session.add(team)
            session.flush()

            item = build_model(NmTeamUser,
            id_team=team.id_team,
            id_user=1,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            self.assertEqual(data['id_team'], team.id_team)
            self.assertEqual(data['id_user'], 1)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
