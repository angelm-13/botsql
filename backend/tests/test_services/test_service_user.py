from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.user_service import UserService


class TestUserService(BackendTestCase):
    def test_crud_service_user(self):
        created = UserService.create(build_payload(UserService, {'created_by': 1, 'date_born': '2026-01-15T12:00:00', 'date_start': '2026-01-15T12:00:00', 'email': 'test@example.com', 'first_name': 'test first_name', 'full_name': 'test first name', 'last_name_father': 'test last name', 'last_name_mother': 'test last name', 'national_id': 'TEST123', 'password': 'test password', 'principal_phone': '5551234567', 'secundary_phone': '5557654321', 'ssn': 'TEST123', 'supervisor': 1, 'base_salary': 10.5, 'hire_date': '2026-01-15', 'tax_id': 'AAA010101AAA', 'title': 'test title', 'user_type': 'admin', 'username': 'test_user', 'puesto': 'test_puesto', 'accepts_marketing': True}))
        self.assertIsNotNone(created)
        page = UserService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
