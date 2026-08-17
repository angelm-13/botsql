from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.user_service import UserService


class TestUserService(BackendTestCase):
    def test_crud_service_user(self):
        created = UserService.create({'created_by': 1, 'date_born': 'datetime.now()', 'date_start': 'datetime.now()', 'email': 'test email', 'first_name': 'test first_name', 'full_name': 'test first_name', 'last_name_father': 'test last_name_father', 'last_name_mother': 'test last_name_mother', 'national_id': 'test national_id', 'password': 'test password', 'principal_phone': 'test principal_phone', 'secundary_phone': 'test secundary_phone', 'ssn': 'test ssn', 'supervisor': 'test_supervisor', 'base_salary': 10.5, 'hire_date': 'datetime.now()', 'tax_id': 'test tax_id', 'title': 'test title', 'user_type': 'admin', 'username': 'test_user', 'puesto': 'test_puesto', 'accepts_marketing': True})
        self.assertIsNotNone(created)
        page = UserService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
