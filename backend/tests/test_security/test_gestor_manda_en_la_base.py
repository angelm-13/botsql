"""El Gestor manda en la base de datos, no solo en la convencion.

Las migraciones se reaplican en cada arranque del pod y muchas reescriben
`entity_permission`; el trigger de
`20260816000000_el_gestor_manda_sobre_las_migraciones.sql` descarta lo que no
venga del Gestor sobre una fila que el Gestor ya toco. Estas pruebas fijan ese
contrato contra PostgreSQL real (el trigger no existe en SQLite).

No heredan de `BackendTestCase` por la misma razon que
`test_kpi_ventas_por_empleado.py`: necesitan el esquema real (init.sql +
migraciones), y `reset_test_database()` lo tiraria. Cada prueba corre dentro de
una transaccion que se revierte, asi que no deja nada.
"""

from __future__ import annotations

import unittest

from sqlalchemy import text

from app.models import EntityPermission
from app.models.session import engine, transaction_context

ENTIDAD = "zz_prueba_gestor"
ROL = 1  # Administrator: lo siembra el bootstrap


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class ElTriggerDelGestor(unittest.TestCase):
    def setUp(self):
        self.conexion = engine.connect()
        self.transaccion = self.conexion.begin()

    def tearDown(self):
        self.transaccion.rollback()
        self.conexion.close()

    def _fila(self, ajustada: bool):
        self.conexion.execute(text(
            "INSERT INTO entity_permission (id_permission, entity_name, scope_create, scope_read,"
            " scope_update, scope_delete, menu_location, menu_label, created_by, ajustado_por_gestor)"
            " VALUES (:rol, :entidad, 0, 4, 0, 0, 'sidebar', 'original', 1,"
            "         CASE WHEN :ajustada THEN now() ELSE NULL END)"
        ), {"rol": ROL, "entidad": ENTIDAD, "ajustada": ajustada})

    def _leer(self):
        return self.conexion.execute(text(
            "SELECT menu_label, scope_create FROM entity_permission"
            " WHERE id_permission = :rol AND entity_name = :entidad"
        ), {"rol": ROL, "entidad": ENTIDAD}).one_or_none()

    def test_una_migracion_sigue_pudiendo_corregir_una_fila_que_el_gestor_no_toco(self):
        self._fila(ajustada=False)
        self.conexion.execute(text(
            "UPDATE entity_permission SET menu_label = 'migracion', scope_create = 4"
            " WHERE entity_name = :entidad"), {"entidad": ENTIDAD})
        self.assertEqual(("migracion", 4), tuple(self._leer()))

    def test_un_update_ajeno_al_gestor_no_pisa_una_fila_ajustada(self):
        self._fila(ajustada=True)
        self.conexion.execute(text(
            "UPDATE entity_permission SET menu_label = 'migracion', scope_create = 4"
            " WHERE entity_name = :entidad"), {"entidad": ENTIDAD})
        self.assertEqual(("original", 0), tuple(self._leer()))

    def test_un_update_que_cambia_la_marca_si_pasa(self):
        """Es lo que hace el ORM al guardar desde el Gestor."""
        self._fila(ajustada=True)
        self.conexion.execute(text(
            "UPDATE entity_permission SET menu_label = 'gestor', ajustado_por_gestor = now() + interval '1 second'"
            " WHERE entity_name = :entidad"), {"entidad": ENTIDAD})
        self.assertEqual("gestor", self._leer()[0])

    def test_un_borrado_fisico_no_se_lleva_una_fila_ajustada(self):
        self._fila(ajustada=True)
        self.conexion.execute(text("DELETE FROM entity_permission WHERE entity_name = :entidad"),
                              {"entidad": ENTIDAD})
        self.assertIsNotNone(self._leer())

    def test_un_borrado_fisico_si_se_lleva_una_fila_que_el_gestor_no_toco(self):
        self._fila(ajustada=False)
        self.conexion.execute(text("DELETE FROM entity_permission WHERE entity_name = :entidad"),
                              {"entidad": ENTIDAD})
        self.assertIsNone(self._leer())

    def test_la_reposicion_de_permisos_de_campo_no_resucita_el_que_el_gestor_retiro(self):
        # Un par campo/rol sin ninguna fila previa: las migraciones ya siembran
        # permisos de campo para casi todo, y uno vigente de antes falsearia el conteo.
        par = self.conexion.execute(text(
            "SELECT f.id_field, p.id_permission FROM field f CROSS JOIN permission p"
            " WHERE NOT EXISTS (SELECT 1 FROM nm_field_permission n"
            "                   WHERE n.id_field = f.id_field AND n.id_permission = p.id_permission)"
            " LIMIT 1")).one_or_none()
        if par is None:
            self.skipTest("la base de prueba no tiene ningun par campo/rol libre")
        id_field, rol = par
        insertar = text(
            "INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by,"
            " deletion_date, ajustado_por_gestor)"
            " VALUES (:campo, :rol, '2', 1, :baja, :marca)")
        # El Gestor retira el permiso: baja logica con marca.
        self.conexion.execute(insertar, {"campo": id_field, "rol": rol, "baja": "2026-10-01", "marca": "2026-10-01"})
        # El INSERT de reposicion de una migracion (sin marca) no debe volver a crearlo.
        self.conexion.execute(insertar, {"campo": id_field, "rol": rol, "baja": None, "marca": None})
        vigentes = self.conexion.execute(text(
            "SELECT count(*) FROM nm_field_permission WHERE id_field = :campo AND id_permission = :rol"
            " AND deletion_date IS NULL"), {"campo": id_field, "rol": rol}).scalar()
        self.assertEqual(0, vigentes)
        # Pero el Gestor si puede volver a concederlo.
        self.conexion.execute(insertar, {"campo": id_field, "rol": rol, "baja": None, "marca": "2026-10-02"})
        vigentes = self.conexion.execute(text(
            "SELECT count(*) FROM nm_field_permission WHERE id_field = :campo AND id_permission = :rol"
            " AND deletion_date IS NULL"), {"campo": id_field, "rol": rol}).scalar()
        self.assertEqual(1, vigentes)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class ElOrmMarcaLoQueTocaElGestor(unittest.TestCase):
    """Sin esta marca el trigger no distingue al Gestor de una migracion."""

    def tearDown(self):
        # La fila la creo el ORM, o sea que esta ajustada y el trigger descartaria
        # un DELETE normal: se apaga solo dentro de esta transaccion.
        with transaction_context() as db:
            db.execute(text("ALTER TABLE entity_permission DISABLE TRIGGER trg_gestor_manda"))
            db.execute(text("DELETE FROM entity_permission WHERE entity_name = :e"), {"e": ENTIDAD})
            db.execute(text("ALTER TABLE entity_permission ENABLE TRIGGER trg_gestor_manda"))

    def test_crear_y_editar_desde_la_aplicacion_fija_y_mueve_la_marca(self):
        with transaction_context() as db:
            fila = EntityPermission(id_permission=ROL, entity_name=ENTIDAD, scope_read=4, created_by=1)
            db.add(fila)
            db.flush()
            id_fila = fila.id_entity_permission
            marca_inicial = fila.ajustado_por_gestor
        self.assertIsNotNone(marca_inicial)

        with transaction_context() as db:
            fila = db.get(EntityPermission, id_fila)
            fila.menu_label = "desde el gestor"
        with transaction_context() as db:
            fila = db.get(EntityPermission, id_fila)
            self.assertEqual("desde el gestor", fila.menu_label)
            self.assertGreater(fila.ajustado_por_gestor, marca_inicial)


if __name__ == "__main__":
    unittest.main()
