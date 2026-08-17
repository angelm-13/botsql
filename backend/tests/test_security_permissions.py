
import unittest

from app.security.permissions import PermissionAction


class SecurityPermissionBitmaskTest(unittest.TestCase):
    def test_bitmask_values(self):
        self.assertEqual(PermissionAction.CREATE, 1)
        self.assertEqual(PermissionAction.READ, 2)
        self.assertEqual(PermissionAction.UPDATE, 4)
        self.assertEqual(PermissionAction.DELETE, 8)

    def test_full_crud_contains_all_actions(self):
        full = 15
        self.assertTrue(full & PermissionAction.CREATE)
        self.assertTrue(full & PermissionAction.READ)
        self.assertTrue(full & PermissionAction.UPDATE)
        self.assertTrue(full & PermissionAction.DELETE)

    def test_read_only_does_not_allow_write(self):
        read_only = 2
        self.assertTrue(read_only & PermissionAction.READ)
        self.assertFalse(read_only & PermissionAction.CREATE)
        self.assertFalse(read_only & PermissionAction.UPDATE)
        self.assertFalse(read_only & PermissionAction.DELETE)


if __name__ == "__main__":
    unittest.main()
