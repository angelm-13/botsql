from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.user import User


class TestUserModel(BackendTestCase):
    def test_create_serialize_summary_delete_user(self):
        with transaction_context() as session:
            item = build_model(User,
            created_by=1,
            date_born='2026-01-15T12:00:00',
            date_start='2026-01-15T12:00:00',
            email='test email',
            first_name='test first_name',
            full_name='test first_name',
            last_name_father='test last_name_father',
            last_name_mother='test last_name_mother',
            national_id='test national_id',
            password='test password',
            principal_phone='test principal_phone',
            secundary_phone='test secundary_phone',
            ssn='test ssn',
            supervisor='test_supervisor',
            base_salary=10.5,
            hire_date='2026-01-15T12:00:00',
            tax_id='test tax_id',
            title='test title',
            user_type='admin',
            username='test_user',
            puesto='test_puesto',
            accepts_marketing=True
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
