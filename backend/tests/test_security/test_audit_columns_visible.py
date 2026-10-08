"""Las columnas de auditoria las ve todo rol que pueda leer el registro.

El gestor de roles no ofrece `created_by`, `creation_date`, `last_update_date`
ni `deletion_date` (nadie las captura), asi que no existen filas de
`nm_field_permission` que las habiliten. Cada ruta recortaba la respuesta a esas
filas y un rol que no fuera administrador nunca veia fecha ni autor.
"""

from __future__ import annotations

import importlib
import pkgutil

import app.routes as rutas
from app.utils.field_access import COLUMNAS_DE_AUDITORIA
from tests.conftest import BackendTestCase


def _rutas_con_recorte_de_campos():
    for info in pkgutil.iter_modules(rutas.__path__):
        modulo = importlib.import_module(f"app.routes.{info.name}")
        if hasattr(modulo, "_field_sets_for_actor"):
            yield info.name, modulo


class TestAuditColumnsVisible(BackendTestCase):
    # Un rol sin una sola fila de permiso de campo.
    ACTOR = {"id_permission": 987654, "user_type": "employee"}

    def test_the_audit_columns_are_a_known_set(self):
        self.assertEqual(
            {"created_by", "creation_date", "last_update_date", "deletion_date"},
            set(COLUMNAS_DE_AUDITORIA),
        )

    def test_every_route_shows_them_to_a_role_without_field_rows(self):
        rutas_probadas = list(_rutas_con_recorte_de_campos())
        self.assertGreater(len(rutas_probadas), 40)
        for nombre, modulo in rutas_probadas:
            with self.subTest(ruta=nombre):
                visibles, _ = modulo._field_sets_for_actor(self.ACTOR)
                self.assertTrue(
                    COLUMNAS_DE_AUDITORIA <= set(visibles),
                    f"{nombre} sigue recortando la auditoria: faltan {COLUMNAS_DE_AUDITORIA - set(visibles)}",
                )

    def test_they_are_never_writable(self):
        """Solo es lectura: nadie atribuye un registro a otra persona."""
        for nombre, modulo in _rutas_con_recorte_de_campos():
            with self.subTest(ruta=nombre):
                _, escribibles = modulo._field_sets_for_actor(self.ACTOR)
                self.assertFalse(COLUMNAS_DE_AUDITORIA & set(escribibles))
