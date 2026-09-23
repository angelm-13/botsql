from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.permission_service import PermissionService


class TestPermissionService(BackendTestCase):
    def test_crud_service_permission(self):
        created = PermissionService.create(build_payload(PermissionService, {'created_by': 1, 'authorized_by': 1, 'permission_description': 'test permission description'}))
        self.assertIsNotNone(created)
        page = PermissionService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def test_list_hides_a_withdrawn_role(self):
        """El selector de rol (Gestor de roles, alta de usuario) no debe enseñar roles retirados.

        `20260828150000_warehouse_roles.sql` genero repetidamente un rol
        "Jefe de almacen" fantasma en cada reinicio del pod porque nada
        filtraba la baja logica al listar -- este test fija que, aunque
        vuelva a pasar algo asi, el listado no lo enseñe.
        """
        from datetime import datetime, timezone

        from app.models.session import transaction_context

        campos_comunes = dict(
            created_by=1, authorized_by=1, id_department=1, id_subdepartment=1, id_level=1,
        )
        with transaction_context() as db:
            db.add_all([
                PermissionService.model(
                    permission_description='rol vigente de prueba', **campos_comunes,
                ),
                PermissionService.model(
                    permission_description='rol retirado de prueba', **campos_comunes,
                    deletion_date=datetime.now(timezone.utc).replace(tzinfo=None),
                ),
            ])
            db.flush()

        page = PermissionService.list(page=1, per_page=500)
        descripciones = {item['permission_description'] for item in page['items']}
        self.assertIn('rol vigente de prueba', descripciones)
        self.assertNotIn('rol retirado de prueba', descripciones)
