"""La unicidad de `nm_team_user` en la base REAL (`init.sql` + todas las migraciones).

Grupo `base_real` de `backend/ci/run_postgres_tests.sh`: no hereda de `BackendTestCase` porque su
`reset_test_database()` tiraria el esquema real. Necesita el bootstrap de siempre (`user=1`).
Su par contra el esquema que arma el ORM es `test_nm_team_user_esquema_orm_postgres.py`: las dos
comparan contra `tests/esquema_equipos.py`, asi que si la migracion y el modelo se separan, una falla.
"""

from __future__ import annotations

import pathlib
import unittest
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.models import NmTeamUser, Team
from app.models.session import engine, transaction_context
from scripts.apply_migrations import _ejecutar_sql_crudo
from tests.esquema_equipos import (
    INDEXDEF_VIGENTE, NOMBRE_CONSTRAINT_ANTERIOR, NOMBRE_INDICE_VIGENTE, indices_unicos_de_nm_team_user,
)

MIGRACION = (
    pathlib.Path(__file__).resolve().parents[3] / "database" / "migrations"
    / "20261022100000_unicidad_nm_team_user_solo_vigentes.sql"
)
PERSONA = 1
NOMBRES = ("lote6 Manzanillo 1", "lote6 Culiacán prueba")


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class UnicidadDeNmTeamUserEnLaBaseRealTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            ids = [fila for fila in db.query(Team.id_team).filter(Team.team_description.in_(NOMBRES))]
            ids = [fila[0] for fila in ids]
            db.execute(delete(NmTeamUser).where(NmTeamUser.id_team.in_(ids)))
            db.execute(delete(Team).where(Team.id_team.in_(ids)))

    def _equipo(self, nombre):
        with transaction_context() as db:
            equipo = Team(team_description=nombre, created_by=1)
            db.add(equipo)
            db.flush()
            return equipo.id_team

    def _membresia(self, id_team, **campos):
        with transaction_context() as db:
            fila = NmTeamUser(id_team=id_team, id_user=PERSONA, created_by=1, **campos)
            db.add(fila)
            db.flush()
            return fila.id_nm_team_user

    def _baja(self, id_membresia, cuando):
        with transaction_context() as db:
            db.get(NmTeamUser, id_membresia).deletion_date = cuando

    def test_la_base_real_tiene_el_indice_parcial_y_ya_no_el_constraint_anterior(self):
        with engine.connect() as conexion:
            indices = indices_unicos_de_nm_team_user(conexion)

        self.assertEqual({NOMBRE_INDICE_VIGENTE: INDEXDEF_VIGENTE}, indices)
        self.assertNotIn(NOMBRE_CONSTRAINT_ANTERIOR, indices)

    def test_dos_membresias_vigentes_iguales_siguen_prohibidas(self):
        equipo = self._equipo(NOMBRES[0])
        self._membresia(equipo)

        with self.assertRaises(IntegrityError):
            self._membresia(equipo)

    def test_baja_y_alta_repetida_deja_el_periodo_viejo_como_historia(self):
        equipo = self._equipo(NOMBRES[0])
        primera = self._membresia(equipo, creation_date=datetime(2026, 10, 5, 12, 0))
        self._baja(primera, datetime(2026, 10, 7, 12, 0))

        segunda = self._membresia(equipo, creation_date=datetime(2026, 10, 9, 12, 0))

        with transaction_context() as db:
            filas = db.query(NmTeamUser).filter_by(id_team=equipo, id_user=PERSONA).order_by(NmTeamUser.creation_date).all()
            self.assertEqual([primera, segunda], [fila.id_nm_team_user for fila in filas])
            self.assertEqual(datetime(2026, 10, 7, 12, 0), filas[0].deletion_date)
            self.assertIsNone(filas[1].deletion_date)

    def test_de_a_a_b_y_de_vuelta_a_a(self):
        equipo_a, equipo_b = self._equipo(NOMBRES[0]), self._equipo(NOMBRES[1])
        en_a = self._membresia(equipo_a, creation_date=datetime(2026, 10, 5, 12, 0))
        self._baja(en_a, datetime(2026, 10, 7, 12, 0))
        en_b = self._membresia(equipo_b, creation_date=datetime(2026, 10, 7, 12, 0))
        self._baja(en_b, datetime(2026, 10, 9, 12, 0))

        de_vuelta = self._membresia(equipo_a, creation_date=datetime(2026, 10, 9, 12, 0))

        with transaction_context() as db:
            periodos = db.query(NmTeamUser).filter(NmTeamUser.id_team.in_([equipo_a, equipo_b])).order_by(NmTeamUser.creation_date).all()
            self.assertEqual([en_a, en_b, de_vuelta], [fila.id_nm_team_user for fila in periodos])
            self.assertEqual([equipo_a, equipo_b, equipo_a], [fila.id_team for fila in periodos])

    def test_reaplicar_la_migracion_en_cada_arranque_no_falla_ni_cambia_nada(self):
        """`db-migrate` corre TODAS las migraciones en cada arranque del pod, sin tabla de control."""
        sql = MIGRACION.read_text(encoding="utf-8")
        for _ in range(2):
            with engine.connect() as conexion:
                _ejecutar_sql_crudo(conexion, sql)
                conexion.commit()

        with engine.connect() as conexion:
            self.assertEqual({NOMBRE_INDICE_VIGENTE: INDEXDEF_VIGENTE}, indices_unicos_de_nm_team_user(conexion))
