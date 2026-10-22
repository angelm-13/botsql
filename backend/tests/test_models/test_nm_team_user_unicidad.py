"""La unicidad de `nm_team_user` es entre membresias VIGENTES, no entre todas.

Corre en SQLite (el indice parcial tambien existe ahi). La misma regla contra el esquema real de
PostgreSQL esta en `tests/test_services/test_nm_team_user_base_real.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.models import NmTeamUser, Team
from app.models.session import transaction_context
from tests.conftest import BackendTestCase

PERSONA = 1


class UnicidadDeMembresiaTest(BackendTestCase):
    def _equipo(self, nombre):
        with transaction_context() as db:
            equipo = Team(team_description=nombre, created_by=1)
            db.add(equipo)
            db.flush()
            return equipo.id_team

    def _membresia(self, id_team, id_user=PERSONA, **campos):
        with transaction_context() as db:
            fila = NmTeamUser(id_team=id_team, id_user=id_user, created_by=1, **campos)
            db.add(fila)
            db.flush()
            return fila.id_nm_team_user

    def _baja(self, id_membresia, cuando):
        with transaction_context() as db:
            db.get(NmTeamUser, id_membresia).deletion_date = cuando

    def test_dos_membresias_vigentes_iguales_siguen_prohibidas(self):
        equipo = self._equipo("Manzanillo 1")
        self._membresia(equipo)

        with self.assertRaises(IntegrityError):
            self._membresia(equipo)

    def test_se_puede_volver_a_agregar_a_quien_ya_se_dio_de_baja_y_la_anterior_queda_como_historia(self):
        equipo = self._equipo("Manzanillo 1")
        primera = self._membresia(equipo, creation_date=datetime(2026, 10, 5, 12, 0))
        self._baja(primera, datetime(2026, 10, 7, 12, 0))

        segunda = self._membresia(equipo, creation_date=datetime(2026, 10, 9, 12, 0))

        self.assertNotEqual(primera, segunda)
        with transaction_context() as db:
            filas = db.query(NmTeamUser).filter_by(id_team=equipo, id_user=PERSONA).order_by(NmTeamUser.creation_date).all()
            self.assertEqual([primera, segunda], [fila.id_nm_team_user for fila in filas])
            self.assertEqual(datetime(2026, 10, 7, 12, 0), filas[0].deletion_date)   # el periodo viejo no se tocó
            self.assertIsNone(filas[1].deletion_date)

    def test_de_a_a_b_y_de_vuelta_a_a_deja_tres_periodos(self):
        equipo_a = self._equipo("Manzanillo 1")
        equipo_b = self._equipo("Culiacán prueba")
        en_a = self._membresia(equipo_a, creation_date=datetime(2026, 10, 5, 12, 0))
        self._baja(en_a, datetime(2026, 10, 7, 12, 0))
        en_b = self._membresia(equipo_b, creation_date=datetime(2026, 10, 7, 12, 0))
        self._baja(en_b, datetime(2026, 10, 9, 12, 0))

        de_vuelta_en_a = self._membresia(equipo_a, creation_date=datetime(2026, 10, 9, 12, 0))

        with transaction_context() as db:
            periodos = db.query(NmTeamUser).filter_by(id_user=PERSONA).order_by(NmTeamUser.creation_date).all()
            self.assertEqual([en_a, en_b, de_vuelta_en_a], [fila.id_nm_team_user for fila in periodos])
            self.assertEqual([equipo_a, equipo_b, equipo_a], [fila.id_team for fila in periodos])
            self.assertEqual(1, sum(fila.deletion_date is None for fila in periodos))   # solo el ultimo sigue vigente

    def test_dos_personas_distintas_pueden_estar_en_el_mismo_equipo(self):
        equipo = self._equipo("Manzanillo 1")
        self._membresia(equipo, id_user=1)
        self._membresia(equipo, id_user=2)

    def test_la_misma_persona_puede_estar_en_dos_equipos_vigentes(self):
        self._membresia(self._equipo("Manzanillo 1"))
        self._membresia(self._equipo("Culiacán prueba"))
