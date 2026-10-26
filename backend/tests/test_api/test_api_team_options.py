"""`/team/options` alimenta el selector de equipos del editor de graficos del Dashboard.

Quien arma un grafico no necesita el modulo `seguridad` (al que pertenece `team`): `GET /team/` le da 403.
`/options` no exige permiso de entidad -- igual que `/user/options` y `/incident_type/options` -- pero si sesion.
"""
from __future__ import annotations

import jwt

from app.models import Team
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestTeamOptions(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Un rol de Dashboard: ve KPIs, pero no tiene ninguna fila de `team`.
                EntityPermission(id_permission=402, entity_name="kpi_definition",
                                  scope_create=0, scope_read=4, scope_update=0, created_by=1),
                Team(id_team=1, team_description="Manzanillo 1", created_by=1),
                Team(id_team=2, team_description="Culiacán prueba", created_by=1),
                Team(id_team=3, team_description="Parque cerrado", created_by=1),
            ])
        # Dado de baja por la API, no escribiendo `deletion_date` a mano.
        self.client.delete("/team/3", headers=self._headers(id_user=1, is_superuser=True))

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def test_un_rol_sin_permiso_de_team_puede_listar_las_opciones(self):
        headers = self._headers(id_user=42, id_permission=402)

        self.assertEqual(403, self.client.get("/team/", headers=headers).status_code)

        respuesta = self.client.get("/team/options", headers=headers)
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual(["Culiacán prueba", "Manzanillo 1"], [x["team_description"] for x in self.json(respuesta)])

    def test_solo_trae_los_equipos_vigentes(self):
        respuesta = self.client.get("/team/options", headers=self._headers(id_user=42, id_permission=402))

        self.assertEqual([1, 2], sorted(x["id_team"] for x in self.json(respuesta)))
        self.assertNotIn("Parque cerrado", [x["team_description"] for x in self.json(respuesta)])

    def test_expone_solo_id_y_nombre(self):
        respuesta = self.client.get("/team/options", headers=self._headers(id_user=42, id_permission=402))

        self.assertTrue(self.json(respuesta))
        for fila in self.json(respuesta):
            self.assertEqual({"id_team", "team_description"}, set(fila))

    def test_exige_sesion(self):
        self.assertEqual(401, self.client.get("/team/options").status_code)

    def test_options_no_se_confunde_con_el_id_de_un_equipo(self):
        # `/team/<id_team>` y `/team/options` conviven: la ruta fija gana.
        self.assertEqual(200, self.client.get("/team/options", headers=self._headers(id_user=42, id_permission=402)).status_code)
        self.assertEqual(200, self.client.get("/team/1", headers=self._headers(id_user=1, is_superuser=True)).status_code)
