"""La dimension `equipo`: un grupo de usuarios (`team`), que en Comala es un parque.

Corre en SQLite y en PostgreSQL: solo toca el catalogo de dimensiones y la resolucion de nombres.
"""

from __future__ import annotations

from datetime import datetime

from app.kpis.dimensiones import DIMENSION_POR_CLAVE, etiquetas_de_dimension
from app.models import Team
from app.models.session import transaction_context
from tests.conftest import BackendTestCase


class DimensionEquipoTest(BackendTestCase):
    def test_se_declara_como_catalogo_cerrado_y_no_como_persona(self):
        equipo = DIMENSION_POR_CLAVE["equipo"]
        self.assertEqual("id_team", equipo.json_key)
        # Su id es `team.id_team`: filtrarlo con ids de usuario compararia cosas distintas.
        self.assertEqual("catalogo", equipo.tipo)
        # Son pocos (parques) y cada uno importa: el Dashboard no los agrupa en "Otros".
        self.assertFalse(equipo.abierta)
        self.assertIsNotNone(equipo.resolver_etiquetas)

    def test_el_backend_resuelve_los_nombres_de_los_equipos(self):
        with transaction_context() as db:
            db.add(Team(id_team=7, team_description="Parque Norte", created_by=1))
            # Un equipo dado de baja conserva su nombre: la historia de los snapshots no se parte.
            db.add(Team(id_team=8, team_description="Parque Viejo", created_by=1, deletion_date=datetime(2026, 1, 1)))

        with transaction_context() as db:
            etiquetas = etiquetas_de_dimension(
                db, "equipo", ({"por_empleado": {"7": 3.0, "8": 1.0, "99": 2.0}}, None),
            )

        self.assertEqual("Parque Norte", etiquetas["7"])
        self.assertEqual("Parque Viejo", etiquetas["8"])
        # Un id sin fila cae a "#id" en lugar de romper la respuesta.
        self.assertEqual("#99", etiquetas["99"])
