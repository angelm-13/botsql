"""El esquema que arma el ORM en PostgreSQL declara el mismo indice que la migracion.

Grupo `esquema_orm` de `backend/ci/run_postgres_tests.sh` (cada prueba recrea el esquema solo con lo
que declara el ORM). Su par contra el esquema real es `test_nm_team_user_base_real.py`: las dos
comparan contra `tests/esquema_equipos.py`.
"""

from __future__ import annotations

import unittest

from app.models.session import engine
from tests.conftest import BackendTestCase
from tests.esquema_equipos import (
    INDEXDEF_VIGENTE, NOMBRE_CONSTRAINT_ANTERIOR, NOMBRE_INDICE_VIGENTE, indices_unicos_de_nm_team_user,
)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class EsquemaOrmDeNmTeamUserTest(BackendTestCase):
    def test_el_orm_declara_el_indice_parcial_y_no_el_constraint_anterior(self):
        with engine.connect() as conexion:
            indices = indices_unicos_de_nm_team_user(conexion)

        self.assertEqual({NOMBRE_INDICE_VIGENTE: INDEXDEF_VIGENTE}, indices)
        self.assertNotIn(NOMBRE_CONSTRAINT_ANTERIOR, indices)
