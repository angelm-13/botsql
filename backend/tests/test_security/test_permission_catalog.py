"""El catalogo del gestor de roles contra el esquema real.

Lo que estas pruebas fijan es la propiedad que se perdio cuando el catalogo era
un JSON escrito a mano: que lo que la pantalla ofrece sea lo que la base tiene.
Medido antes del cambio -- 51 de 85 entidades, y a 14 de esas les faltaban
columnas que la tabla si tiene.
"""

from __future__ import annotations

import unittest

import app.models  # noqa: F401  (registra todos los modelos)
from app.models.base import Base
from app.modules import registry
from app.modules.catalogo import COLUMNAS_DE_SISTEMA, catalogo_base


class TestCatalogoDePermisos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo = catalogo_base()
        cls.por_nombre = {e["entity_name"]: e for e in cls.catalogo["entities"]}

    def test_every_entity_of_the_registry_is_offered(self):
        """Lo que no sale en el catalogo no se puede conceder ni quitar."""
        declaradas = {e for m in registry.MODULOS for e in m.entidades}

        faltantes = sorted(declaradas - set(self.por_nombre))

        self.assertEqual(
            [], faltantes,
            "Estas entidades pertenecen a un modulo pero el gestor de roles no "
            "las ofrece: " + ", ".join(faltantes),
        )

    def test_every_capability_of_the_registry_is_offered(self):
        declaradas = {c.clave for c in registry.CAPACIDADES}

        self.assertTrue(declaradas <= set(self.por_nombre))

    def test_each_entity_carries_the_columns_its_table_really_has(self):
        """El desfase que este catalogo existe para no volver a tener."""
        for entidad, entrada in self.por_nombre.items():
            # Por el registro, no por `Base.metadata`: `restaurant_waiter` es
            # capacidad Y tabla, y preguntarle a los modelos la daria por tabla.
            if entidad not in registry.ENTIDAD_A_MODULO:
                continue
            tabla = Base.metadata.tables[entidad]
            reales = {c.name for c in tabla.columns}
            declaradas = {c["field_name"] for c in entrada["fields"]}
            with self.subTest(entidad=entidad):
                self.assertEqual(reales, declaradas)

    def test_a_capability_offers_actions_and_not_fields(self):
        """Una capacidad no es una tabla: no tiene columnas que conceder."""
        for capacidad in registry.CAPACIDADES:
            entrada = self.por_nombre[capacidad.clave]
            with self.subTest(capacidad=capacidad.clave):
                self.assertEqual("actions_only", entrada["permission_scope"])
                self.assertEqual([], entrada["fields"])

    def test_a_capability_named_like_a_table_still_offers_no_fields(self):
        """`restaurant_waiter` es capacidad Y tabla real del restaurante.

        Si el catalogo resolviera por nombre de tabla en vez de por lo que el
        registro declara, la capacidad "Meseros" pediria marcar las columnas de
        una tabla que no gobierna.
        """
        self.assertIn("restaurant_waiter", Base.metadata.tables)

        entrada = self.por_nombre["restaurant_waiter"]
        self.assertEqual("actions_only", entrada["permission_scope"])
        self.assertEqual([], entrada["fields"])

    def test_a_foreign_key_says_where_it_points(self):
        """Es lo que hace visible la relacion en la pantalla."""
        renglon = self.por_nombre["nm_incident_product"]
        campos = {c["field_name"]: c for c in renglon["fields"]}

        self.assertTrue(campos["id_incident"]["is_foreign"])
        self.assertEqual("incident", campos["id_incident"]["reference_table"])
        self.assertEqual("id_incident", campos["id_incident"]["reference_field"])

        # Y una columna que no es llave no dice apuntar a ningun lado.
        self.assertFalse(campos["quantity"]["is_foreign"])
        self.assertIsNone(campos["quantity"]["reference_table"])

    def test_the_system_columns_are_marked_as_such(self):
        """La pantalla las oculta por esta marca; nadie las captura a mano."""
        for entrada in self.catalogo["entities"]:
            for campo in entrada["fields"]:
                with self.subTest(entidad=entrada["entity_name"], campo=campo["field_name"]):
                    self.assertEqual(
                        campo["field_name"] in COLUMNAS_DE_SISTEMA,
                        campo["is_system_field"],
                    )

    def test_entities_are_grouped_by_their_module_and_not_by_a_second_vocabulary(self):
        """Habia dos vocabularios: `hr`/`scm`/`erp` en el catalogo y las claves
        del registro en todo lo demas. `incident` salia en CRM siendo de
        Operaciones, y `ticket` fuera de Facturacion.
        """
        for entidad, modulo in registry.ENTIDAD_A_MODULO.items():
            with self.subTest(entidad=entidad):
                self.assertEqual(modulo, self.por_nombre[entidad]["module"])
                self.assertEqual(modulo, self.por_nombre[entidad]["domain"])

    def test_every_entity_is_named_in_spanish(self):
        """El catalogo viejo las nombraba humanizando la tabla en ingles."""
        for entidad, entrada in self.por_nombre.items():
            with self.subTest(entidad=entidad):
                self.assertTrue(entrada["label"])
                self.assertNotEqual(entidad, entrada["label"])

    def test_the_bootstrap_only_entities_are_flagged(self):
        for entidad in registry.SOLO_ARRANQUE:
            if entidad not in self.por_nombre:
                continue          # `password_reset_token` no es entidad de modulo
            with self.subTest(entidad=entidad):
                self.assertTrue(self.por_nombre[entidad]["is_bootstrap_only"])


if __name__ == "__main__":
    unittest.main()
