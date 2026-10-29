"""El 409 de "no se puede borrar" dice que registros lo impiden, y cuantos ya estan dados de baja."""

from __future__ import annotations

import jwt

from app.services.related_records import delete_has_related_records_error, related_records
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ANA = 11


class RegistrosRelacionadosTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        token = jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {token}"}

    def _en_un_equipo(self, id_user):
        equipo = self.client.post("/team/", json={"team_description": "Taller"}, headers=self.headers)
        self.assertEqual(201, equipo.status_code, self.json(equipo))
        membresia = self.client.post(
            "/nm_team_user/",
            json={"id_team": self.json(equipo)["id_team"], "id_user": id_user},
            headers=self.headers,
        )
        self.assertEqual(201, membresia.status_code, self.json(membresia))
        return self.json(membresia)["id_nm_team_user"]

    def _de(self, id_user, tabla):
        return next((fila for fila in related_records("user", id_user) if fila["table"] == tabla), None)

    def test_dice_en_que_tabla_hay_registros_y_cuantos(self):
        self._en_un_equipo(ANA)

        self.assertEqual({"table": "nm_team_user", "count": 1, "deleted_count": 0}, self._de(ANA, "nm_team_user"))

    def test_una_baja_logica_sigue_contando_pero_se_marca_aparte(self):
        membresia = self._en_un_equipo(ANA)
        self.client.delete(f"/nm_team_user/{membresia}", headers=self.headers)

        self.assertEqual({"table": "nm_team_user", "count": 1, "deleted_count": 1}, self._de(ANA, "nm_team_user"))

    def test_el_id_puede_llegar_como_texto_de_la_ruta(self):
        self._en_un_equipo(ANA)

        self.assertEqual(1, self._de(str(ANA), "nm_team_user")["count"])

    def test_sin_registros_ligados_no_devuelve_nada_y_una_tabla_desconocida_tampoco(self):
        self.assertIsNone(self._de(ANA, "nm_team_user"))
        self.assertEqual([], related_records("no_existe", 1))

    def test_el_error_lleva_el_detalle_en_meta(self):
        self._en_un_equipo(ANA)

        error = delete_has_related_records_error("user", "user", ANA)

        self.assertEqual("errors.delete_has_related_records", error.message_key)
        self.assertEqual(409, error.status_code)
        self.assertEqual("user", error.meta["entity"])
        self.assertIn("nm_team_user", [fila["table"] for fila in error.meta["related"]])

    def test_sin_id_el_error_sale_igual_con_la_lista_vacia(self):
        self.assertEqual([], delete_has_related_records_error("user", "user", None).meta["related"])
