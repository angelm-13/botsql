from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.routes.auth import _user_payload
from app.services.product_service import ProductService
from app.utils.auth import _has_entity_permission
from app.utils.errors import AppError


class TestTenantIdentity(unittest.TestCase):
    def test_internal_token_payload_contains_user_project(self):
        user = SimpleNamespace(
            id_user=9,
            id_proyect=27,
            username='tenant-user',
            user_type='employee',
            id_permission=4,
        )

        payload = _user_payload(user)

        self.assertEqual(payload['id_proyect'], 27)

    def test_non_bootstrap_admin_requires_persisted_permission(self):
        user_data = {'user_type': 'admin', 'id_permission': None}

        self.assertFalse(_has_entity_permission(user_data, 'product', 'read'))

    def test_product_scope_rejects_missing_project(self):
        with self.assertRaises(AppError) as raised:
            ProductService._project_id({'id_user': 9})

        self.assertEqual(raised.exception.status_code, 403)

    def test_product_outside_project_is_hidden(self):
        session = SimpleNamespace(scalar=lambda statement: None)
        context = unittest.mock.MagicMock()
        context.__enter__.return_value = session
        context.__exit__.return_value = False

        with patch('app.services.product_service.transaction_context', return_value=context):
            with self.assertRaises(AppError) as raised:
                ProductService.require_record_scope(91, {'id_user': 9, 'id_proyect': 27})

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.message_key, 'errors.resource_not_found')

    def test_bootstrap_admin_keeps_global_scope(self):
        with patch('app.services.product_service.transaction_context') as transaction:
            ProductService.require_record_scope(91, {'is_bootstrap_admin': True})

        transaction.assert_not_called()


if __name__ == '__main__':
    unittest.main()