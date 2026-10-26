"""Equipos y membresias se dan de baja, no se borran: la historia de quien estuvo en que equipo se conserva.

Corre en SQLite (la API de `team` y `nm_team_user` no usa nada exclusivo de PostgreSQL). Los KPIs con un equipo
dado de baja estan abajo, en `EquipoDadoDeBajaEnLosKpisTest`.
"""

from __future__ import annotations

import jwt

from app.models import EventLog, NmTeamUser, Team
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ANA, BETO = 11, 12


class BajaLogicaDeEquiposApiTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        token = jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {token}"}

    # --- ayudas -----------------------------------------------------------------------------------

    def _equipo(self, nombre):
        respuesta = self.client.post("/team/", json={"team_description": nombre}, headers=self.headers)
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        return self.json(respuesta)["id_team"]

    def _agrega(self, id_team, id_user):
        return self.client.post("/nm_team_user/", json={"id_team": id_team, "id_user": id_user}, headers=self.headers)

    def _membresia(self, id_team, id_user):
        respuesta = self._agrega(id_team, id_user)
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        return self.json(respuesta)["id_nm_team_user"]

    def _ids_de(self, ruta, campo):
        respuesta = self.client.get(f"{ruta}?per_page=100", headers=self.headers)
        self.assertEqual(200, respuesta.status_code)
        return [fila[campo] for fila in self.json(respuesta)["items"]]

    def _fila(self, modelo, id_):
        with transaction_context() as db:
            fila = db.get(modelo, id_)
            return None if fila is None else fila.serialize()

    # --- dar de baja un equipo ----------------------------------------------------------------------

    def test_dar_de_baja_un_equipo_no_borra_la_fila_y_lo_saca_de_los_listados(self):
        norte, sur = self._equipo("Manzanillo 1"), self._equipo("Culiacán prueba")

        respuesta = self.client.delete(f"/team/{norte}", headers=self.headers)

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual([sur], self._ids_de("/team/", "id_team"))
        fila = self._fila(Team, norte)
        self.assertIsNotNone(fila, "la fila sigue ahi: la baja es logica")
        self.assertIsNotNone(fila["deletion_date"])
        listado = self.json(self.client.get("/team/", headers=self.headers))
        self.assertEqual(1, listado["total"], "el total cuenta solo los vigentes")

    def test_un_equipo_dado_de_baja_ya_no_se_puede_leer_ni_editar(self):
        norte = self._equipo("Manzanillo 1")
        self.client.delete(f"/team/{norte}", headers=self.headers)

        self.assertEqual(404, self.client.get(f"/team/{norte}", headers=self.headers).status_code)
        respuesta = self.client.put(f"/team/{norte}", json={"team_description": "Otro"}, headers=self.headers)
        self.assertEqual(404, respuesta.status_code)

    def test_darlo_de_baja_dos_veces_no_vuelve_a_fecharlo(self):
        norte = self._equipo("Manzanillo 1")
        self.client.delete(f"/team/{norte}", headers=self.headers)
        primera = self._fila(Team, norte)["deletion_date"]

        respuesta = self.client.delete(f"/team/{norte}", headers=self.headers)

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual(primera, self._fila(Team, norte)["deletion_date"])

    def test_un_equipo_que_no_existe_da_404_al_darlo_de_baja(self):
        self.assertEqual(404, self.client.delete("/team/99999", headers=self.headers).status_code)

    def test_la_baja_del_equipo_da_de_baja_sus_membresias_vigentes_en_el_mismo_instante(self):
        norte = self._equipo("Manzanillo 1")
        ana, beto = self._membresia(norte, ANA), self._membresia(norte, BETO)
        self.client.delete(f"/nm_team_user/{beto}", headers=self.headers)       # Beto ya se habia ido
        salida_de_beto = self._fila(NmTeamUser, beto)["deletion_date"]

        self.client.delete(f"/team/{norte}", headers=self.headers)

        equipo = self._fila(Team, norte)
        self.assertEqual(equipo["deletion_date"], self._fila(NmTeamUser, ana)["deletion_date"],
                         "la membresia vigente cae con el equipo, en el mismo instante")
        self.assertEqual(salida_de_beto, self._fila(NmTeamUser, beto)["deletion_date"],
                         "la que ya estaba de baja conserva su fecha: no se pierde cuando se fue de verdad")
        self.assertEqual([], self._ids_de("/nm_team_user/", "id_nm_team_user"))

    def test_la_baja_deja_rastro_en_el_event_log_del_equipo_y_de_sus_membresias(self):
        norte = self._equipo("Manzanillo 1")
        self._membresia(norte, ANA)

        self.client.delete(f"/team/{norte}", headers=self.headers)

        with transaction_context() as db:
            bajas = {fila.table_name for fila in db.query(EventLog).filter_by(action="delete")}
        self.assertEqual({"team", "nm_team_user"}, bajas)

    # --- quitar y volver a agregar a una persona -------------------------------------------------------

    def test_quitar_a_alguien_de_un_equipo_da_de_baja_su_membresia_y_no_la_borra(self):
        norte = self._equipo("Manzanillo 1")
        membresia = self._membresia(norte, ANA)

        respuesta = self.client.delete(f"/nm_team_user/{membresia}", headers=self.headers)

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual([], self._ids_de("/nm_team_user/", "id_nm_team_user"))
        self.assertIsNotNone(self._fila(NmTeamUser, membresia)["deletion_date"])
        self.assertEqual(404, self.client.get(f"/nm_team_user/{membresia}", headers=self.headers).status_code)

    def test_volver_a_agregar_a_quien_se_dio_de_baja_crea_una_membresia_nueva_y_la_anterior_queda_de_historia(self):
        norte = self._equipo("Manzanillo 1")
        primera = self._membresia(norte, ANA)
        self.client.delete(f"/nm_team_user/{primera}", headers=self.headers)
        baja_de_la_primera = self._fila(NmTeamUser, primera)["deletion_date"]

        segunda = self._membresia(norte, ANA)

        self.assertNotEqual(primera, segunda)
        self.assertEqual([segunda], self._ids_de("/nm_team_user/", "id_nm_team_user"), "el listado solo trae la vigente")
        self.assertEqual(baja_de_la_primera, self._fila(NmTeamUser, primera)["deletion_date"], "el periodo viejo no se toco")
        self.assertIsNone(self._fila(NmTeamUser, segunda)["deletion_date"])

    def test_de_a_a_b_y_de_vuelta_a_a_deja_tres_periodos(self):
        a, b = self._equipo("Manzanillo 1"), self._equipo("Culiacán prueba")
        en_a = self._membresia(a, ANA)
        self.client.delete(f"/nm_team_user/{en_a}", headers=self.headers)
        en_b = self._membresia(b, ANA)
        self.client.delete(f"/nm_team_user/{en_b}", headers=self.headers)

        de_vuelta = self._membresia(a, ANA)

        with transaction_context() as db:
            periodos = db.query(NmTeamUser).filter_by(id_user=ANA).order_by(NmTeamUser.id_nm_team_user).all()
            self.assertEqual([en_a, en_b, de_vuelta], [fila.id_nm_team_user for fila in periodos])
            self.assertEqual([a, b, a], [fila.id_team for fila in periodos])
            self.assertEqual([False, False, True], [fila.deletion_date is None for fila in periodos])

    def test_agregar_a_quien_ya_esta_vigente_en_ese_equipo_da_409_con_mensaje_claro(self):
        norte = self._equipo("Manzanillo 1")
        self._membresia(norte, ANA)

        respuesta = self._agrega(norte, ANA)

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.team_member_duplicate", self.json(respuesta)["error_key"])
        self.assertEqual(1, len(self._ids_de("/nm_team_user/", "id_nm_team_user")))

    def test_no_se_puede_agregar_a_alguien_a_un_equipo_dado_de_baja(self):
        norte = self._equipo("Manzanillo 1")
        self.client.delete(f"/team/{norte}", headers=self.headers)

        respuesta = self._agrega(norte, ANA)

        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.team_not_available", self.json(respuesta)["error_key"])

    def test_agregar_sin_equipo_o_sin_persona_sigue_dando_el_400_de_siempre(self):
        respuesta = self.client.post("/nm_team_user/", json={"id_user": ANA}, headers=self.headers)
        self.assertEqual(400, respuesta.status_code)

    # --- el nombre es unico entre los equipos vigentes ---------------------------------------------------

    def test_dos_equipos_vigentes_no_pueden_llamarse_igual(self):
        self._equipo("Manzanillo 1")

        respuesta = self.client.post("/team/", json={"team_description": "Manzanillo 1"}, headers=self.headers)

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.team_name_duplicate", self.json(respuesta)["error_key"])
        self.assertEqual(1, len(self._ids_de("/team/", "id_team")))

    def test_mayusculas_y_espacios_de_los_lados_no_hacen_distinto_al_nombre(self):
        self._equipo("Manzanillo 1")

        for repetido in ("manzanillo 1", "  MANZANILLO 1  "):
            respuesta = self.client.post("/team/", json={"team_description": repetido}, headers=self.headers)
            self.assertEqual(409, respuesta.status_code, repetido)

    def test_el_nombre_se_guarda_sin_espacios_de_los_lados(self):
        self.assertEqual("Culiacán prueba", self._fila(Team, self._equipo("  Culiacán prueba "))["team_description"])

    def test_el_nombre_de_un_equipo_dado_de_baja_se_puede_volver_a_usar(self):
        viejo = self._equipo("Manzanillo 1")
        self.client.delete(f"/team/{viejo}", headers=self.headers)

        nuevo = self._equipo("Manzanillo 1")

        self.assertNotEqual(viejo, nuevo)

    def test_renombrar_a_un_nombre_que_ya_tiene_otro_equipo_vigente_da_409(self):
        self._equipo("Manzanillo 1")
        sur = self._equipo("Culiacán prueba")

        respuesta = self.client.put(f"/team/{sur}", json={"team_description": "manzanillo 1"}, headers=self.headers)

        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("Culiacán prueba", self._fila(Team, sur)["team_description"])

    def test_guardar_un_equipo_con_su_propio_nombre_no_choca_consigo_mismo(self):
        norte = self._equipo("Manzanillo 1")

        respuesta = self.client.put(f"/team/{norte}", json={"team_description": "Manzanillo 1"}, headers=self.headers)

        self.assertEqual(200, respuesta.status_code)

    def test_renombrar_es_seguro_conserva_el_id_y_las_membresias(self):
        norte = self._equipo("Manzanillo 1")
        membresia = self._membresia(norte, ANA)

        respuesta = self.client.put(f"/team/{norte}", json={"team_description": "Manzanillo Norte"}, headers=self.headers)

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual(norte, self.json(respuesta)["id_team"])
        self.assertEqual("Manzanillo Norte", self._fila(Team, norte)["team_description"])
        fila = self._fila(NmTeamUser, membresia)
        self.assertEqual((norte, ANA), (fila["id_team"], fila["id_user"]))
        self.assertIsNone(fila["deletion_date"])
