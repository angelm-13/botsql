from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.theme import Theme


class TestThemeModel(BackendTestCase):
    def test_create_serialize_summary_delete_theme(self):
        with transaction_context() as session:
            item = Theme(
            created_by=1,
            tenant_id=1,
            primary_color='#0D47A1',
            secondary_color='#0D47A1',
            background_color='#0D47A1',
            text_color='#0D47A1',
            highlight_color='#0D47A1',
            success_color='#0D47A1',
            error_color='#0D47A1'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
