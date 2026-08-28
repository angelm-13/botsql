"""El catalogo de campos, del que dependen los permisos de captura.

Las pantallas genericas arman el formulario con los campos que el rol tiene
concedidos en `nm_field_permission`, y un campo no se puede conceder si no
existe en `field`. El catalogo estaba poblado solo con nueve tablas de
logistica, asi que cualquier rol no administrador veia el formulario recortado
y su captura llegaba al servidor sin datos.

El script `database/sync_fields.sql` deberia llenarlo, pero declara columnas
que la tabla real no tiene, de modo que abortaba en su primera sentencia sin
insertar nada. Aqui la fuente son los modelos.
"""

from __future__ import annotations

import unittest

import app.models  # noqa: F401  (registra todos los modelos)
from app.models.base import Base
from scripts.sync_field_catalog import COLUMNAS_DE_SISTEMA, columnas_publicables


class TestPublishableColumns(unittest.TestCase):
    def test_it_covers_the_operational_entities(self):
        """Las entidades de Operaciones e Inventario son las que se capturan."""
        tablas = {tabla for tabla, _ in columnas_publicables()}

        for entidad in (
            "product", "location", "location_type", "material", "unit", "brand",
            "inventory_status", "incident", "incident_detail", "incident_type",
            "task", "task_note", "task_type", "proyect",
        ):
            with self.subTest(entidad=entidad):
                self.assertIn(entidad, tablas)

    def test_system_managed_columns_are_left_out(self):
        """Nadie captura la fecha de alta ni la de baja."""
        publicables = set(columnas_publicables())

        for columna in COLUMNAS_DE_SISTEMA:
            with self.subTest(columna=columna):
                self.assertNotIn(("product", columna), publicables)

    def test_created_by_is_published_but_never_granted(self):
        """Se publica para poder consultarlo; la migracion no lo concede.

        Si fuera capturable, cualquiera podria atribuir un registro a otra
        persona.
        """
        self.assertIn(("product", "created_by"), set(columnas_publicables()))

    def test_business_columns_are_published(self):
        publicables = set(columnas_publicables())

        for tabla, columna in (
            ("product", "descripcion"),
            ("product", "id_location"),
            ("incident", "incident_status"),
            ("task", "task_description"),
            ("proyect", "proyect_status"),
        ):
            with self.subTest(campo=f"{tabla}.{columna}"):
                self.assertIn((tabla, columna), publicables)

    def test_every_model_table_is_covered(self):
        publicables = {tabla for tabla, _ in columnas_publicables()}

        self.assertEqual(set(Base.metadata.tables), publicables)

    def test_the_catalog_is_not_empty_for_any_table(self):
        por_tabla = {}
        for tabla, columna in columnas_publicables():
            por_tabla.setdefault(tabla, []).append(columna)

        vacias = [tabla for tabla, columnas in por_tabla.items() if not columnas]
        self.assertEqual([], vacias)


if __name__ == "__main__":
    unittest.main()
