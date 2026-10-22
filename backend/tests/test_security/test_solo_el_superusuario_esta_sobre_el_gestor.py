"""Solo el superusuario esta por encima del Gestor de roles y permisos.

`user_type` ("admin", "employee"...) es la naturaleza de la cuenta, no un
permiso: quien administra una instalacion lo hace con el rol que se le asigno,
y ese rol manda -en entidades, en campos y en las pantallas del propio Gestor.
Antes ~55 rutas daban visibilidad y escritura total de campos a cualquier
`user_type == "admin"`, aunque su rol fuera restringido.
"""
from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path

import jwt

import app.routes as rutas
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils import scope
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ADMIN_SIN_PERMISOS = {"user_type": "admin", "id_permission": 999, "id_user": 7}
SUPERUSUARIO = {"user_type": "admin", "id_permission": 1, "id_user": 1, "is_superuser": True}
ROL_GESTOR, ROL_TIMBRADO = 601, 602


def _modulos_con_acceso_total_a_campos():
    for info in pkgutil.iter_modules(rutas.__path__):
        modulo = importlib.import_module(f"app.routes.{info.name}")
        funcion = getattr(modulo, "_actor_has_unrestricted_field_access", None)
        if funcion is not None:
            yield info.name, funcion


class TestSoloElSuperusuarioEstaSobreElGestor(BackendTestCase):
    def _headers(self, id_permission, **claims):
        claims = {"id_user": 41, "username": "cliente", "user_type": "admin",
                  "id_permission": id_permission, **claims}
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def test_user_type_admin_does_not_unlock_every_field_in_any_route(self):
        modulos = list(_modulos_con_acceso_total_a_campos())
        self.assertGreater(len(modulos), 40)  # el patron sigue repartido por las rutas
        for nombre, funcion in modulos:
            with self.subTest(ruta=nombre):
                self.assertFalse(funcion(ADMIN_SIN_PERMISOS))
                self.assertTrue(funcion(SUPERUSUARIO))

    def test_the_shared_scope_helper_only_trusts_the_superuser(self):
        self.assertFalse(scope._sin_restriccion(ADMIN_SIN_PERMISOS))
        self.assertTrue(scope._sin_restriccion(SUPERUSUARIO))
        self.assertTrue(scope._sin_restriccion({"is_bootstrap_admin": True}))

    def test_the_role_manager_catalog_follows_the_entity_permission(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=ROL_GESTOR, entity_name="entity_permission",
                                    scope_read=4, created_by=1))

        sin_permiso = self.client.get("/security/permission-catalog", headers=self._headers(999))
        con_permiso = self.client.get("/security/permission-catalog", headers=self._headers(ROL_GESTOR))

        self.assertEqual(403, sin_permiso.status_code)
        self.assertEqual(200, con_permiso.status_code)

    def test_the_stamping_config_follows_fiscal_stamp_in_the_role_manager(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=ROL_TIMBRADO, entity_name="fiscal_stamp",
                                    scope_read=4, scope_update=4, created_by=1))

        sin_permiso = self.client.get("/stamping/config", headers=self._headers(999))
        con_permiso = self.client.get("/stamping/config", headers=self._headers(ROL_TIMBRADO))

        self.assertEqual(403, sin_permiso.status_code)
        self.assertNotEqual(403, con_permiso.status_code)

    def test_resetting_someone_elses_mfa_needs_to_edit_users_in_the_role_manager(self):
        respuesta = self.client.post("/auth/mfa/reset/5", headers=self._headers(999))

        self.assertEqual(403, respuesta.status_code)

    def test_no_code_grants_authority_by_user_type(self):
        """`user_type` describe la cuenta; no da autoridad ni rango.

        La unica coincidencia permitida es la amarra de identidad del superusuario
        (usuario `admin1` Y tipo `admin`, `_is_bootstrap_admin` en `routes/auth.py`):
        no concede nada, solo reconoce quien es el bootstrap.
        """
        raiz = Path(__file__).resolve().parents[2] / "app"
        patron = re.compile(r"""user_type.*['"]admin['"]|USER_HIERARCHY_RANKS|COMPANY_ADMIN_USER_TYPES|_user_hierarchy_rank""")
        encontrados = {}
        for archivo in raiz.rglob("*.py"):
            coincidencias = [linea.strip() for linea in archivo.read_text(encoding="utf-8").splitlines()
                             if patron.search(linea) and not linea.lstrip().startswith("#")]
            if coincidencias:
                encontrados[archivo.relative_to(raiz).as_posix()] = coincidencias

        # Las unicas menciones de 'admin' como TIPO son la amarra del bootstrap y el
        # enum de la columna (models/user.py), que solo lista los valores validos.
        self.assertEqual({"routes/auth.py", "models/user.py"}, set(encontrados), encontrados)
        self.assertEqual(1, len(encontrados["routes/auth.py"]), encontrados["routes/auth.py"])
