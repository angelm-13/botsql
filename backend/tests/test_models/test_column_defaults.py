"""Coherencia de los valores por omision declarados en los modelos.

Estas comprobaciones existen por dos fallas reales que las pruebas normales no
podian ver, porque corren sobre SQLite y el problema solo aparece en
PostgreSQL:

1. Una columna booleana declarada con `server_default=text('0')`. SQLite
   guarda los booleanos como enteros y lo acepta; PostgreSQL rechaza la
   creacion de la tabla con "column is of type boolean but default expression
   is of type integer". El esquema no se podia crear en una base nueva y
   ninguna de las 645 pruebas lo detectaba.

2. Una columna NOT NULL cuyo valor por omision vivia solo en Python
   (`default=`) y no en la base (`server_default=`). Cuando el esquema lo crea
   el arranque a partir de los modelos, la columna queda sin valor por omision
   y cualquier INSERT en SQL directo que la omita falla. Eso abortaba
   `seed.sql` en su primer renglon, y con el se quedaban sin sembrar todos los
   catalogos que venian despues.

La primera se comprueba compilando el DDL con el dialecto de PostgreSQL, que es
la unica forma fiel de saber que va a generar el arranque. No sirve inspeccionar
el valor declarado: `server_default="texto"` es correcto porque SQLAlchemy lo
entrecomilla, mientras `server_default=text("0")` se escribe tal cual.
"""

from __future__ import annotations

import unittest

from sqlalchemy import Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models  # noqa: F401  (registra todos los modelos en el metadata)
from app.models.base import Base


# Frentes de trabajo ajenos a facturacion, inventario y operaciones. Sus
# columnas con valor por omision solo en Python quedan pendientes de su propio
# frente; se excluyen para que esta prueba no dependa de trabajo de otros.
OTROS_FRENTES = ("restaurant", "appointment", "availability", "calendar")

# Excepciones deliberadas dentro de este frente.
SIN_SERVER_DEFAULT_A_PROPOSITO = {
    # Columna de auditoria: poner un autor por omision en la base ocultaria
    # filas creadas sin autor, que es peor que el estado actual.
    "entity_permission.created_by",
    # El valor se construye por fila, no es una constante.
    "audit_log.metadata_json",
}


def _postgres_ddl(table) -> str:
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


class TestBooleanDefaultsCompileForPostgres(unittest.TestCase):
    def test_every_boolean_default_renders_as_true_or_false(self):
        """`DEFAULT 0` en una columna booleana impide crear la tabla."""
        malas = []
        for table in Base.metadata.tables.values():
            booleanas = {
                column.name for column in table.columns
                if isinstance(column.type, Boolean) and column.server_default is not None
            }
            if not booleanas:
                continue
            for linea in _postgres_ddl(table).splitlines():
                texto = linea.strip().rstrip(",")
                nombre = texto.split()[0].strip('"') if texto else ""
                if nombre not in booleanas or "DEFAULT" not in texto:
                    continue
                # La linea es `col BOOLEAN DEFAULT false NOT NULL`: interesa
                # solo la primera palabra despues de DEFAULT.
                resto = texto.split("DEFAULT", 1)[1].split()
                valor = resto[0].rstrip(",").strip("'\"").lower() if resto else ""
                if valor not in {"true", "false"}:
                    malas.append(f"{table.name}.{nombre} -> DEFAULT {valor}")

        self.assertEqual(
            [], malas,
            "En PostgreSQL una columna booleana no acepta un numero como valor por "
            f"omision; usa text('true') o text('false'): {malas}",
        )

    def test_the_whole_schema_compiles_for_postgres(self):
        """Si el DDL no compila, el arranque no puede crear la base."""
        for table in Base.metadata.tables.values():
            with self.subTest(tabla=table.name):
                self.assertIn("CREATE TABLE", _postgres_ddl(table))


class TestPythonOnlyDefaults(unittest.TestCase):
    """Columnas NOT NULL cuyo valor por omision no llega a la base.

    Rompen cualquier INSERT en SQL directo que las omita, que es como se
    aplican las semillas y las migraciones de datos.
    """

    @staticmethod
    def _python_only():
        encontradas = set()
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if column.nullable or column.primary_key:
                    continue
                if column.server_default is not None or column.default is None:
                    continue
                encontradas.add(f"{table.name}.{column.name}")
        return encontradas

    def test_none_remain_in_invoicing_inventory_or_operations(self):
        pendientes = {
            nombre for nombre in self._python_only()
            if not nombre.startswith(OTROS_FRENTES)
        } - SIN_SERVER_DEFAULT_A_PROPOSITO

        self.assertEqual(
            set(), pendientes,
            "Columna NOT NULL con valor por omision solo en Python. Rompe el SQL "
            "directo (semillas, migraciones de datos). Agrega server_default, o "
            f"registrala como excepcion con su razon: {sorted(pendientes)}",
        )

    def test_the_columns_that_broke_the_seed_are_fixed(self):
        """Las que abortaban seed.sql deben tener el valor en la base."""
        for nombre in (
            "customer_supplier.is_principal",
            "entity_permission.menu_location",
            "entity_permission.menu_order",
            "entity_permission.scope_create",
            "entity_permission.scope_read",
            "entity_permission.scope_update",
            "entity_permission.scope_delete",
            "invoice.manual_capture",
            "proyect.proyect_status",
            "location_type.is_warehouse",
            "invoice_material_service.iva_exempt",
        ):
            tabla, columna = nombre.split(".")
            with self.subTest(columna=nombre):
                self.assertIsNotNone(
                    Base.metadata.tables[tabla].columns[columna].server_default,
                    f"{nombre} necesita server_default para que el SQL directo la pueda omitir",
                )

    def test_the_pending_ones_are_only_from_other_work_streams(self):
        """Deja constancia de lo que queda, sin fallar por trabajo ajeno."""
        pendientes = sorted(self._python_only() - SIN_SERVER_DEFAULT_A_PROPOSITO)
        self.assertTrue(
            all(nombre.startswith(OTROS_FRENTES) for nombre in pendientes),
            f"Quedan columnas pendientes fuera de restaurante y citas: {pendientes}",
        )


class TestDeferrableForeignKeys(unittest.TestCase):
    """Las llaves foraneas deben poder aplazarse durante la siembra.

    `seed.sql` no podia aplicarse a una base limpia: su orden no respeta las
    dependencias, y ademas user, permission, proyect y customer_supplier se
    referencian en circulo con columnas obligatorias, de modo que ningun orden
    de sentencias habria funcionado. La salida es que la comprobacion se
    aplace al COMMIT, y para eso las llaves tienen que ser diferibles.

    Se comprueba sobre el metadata porque el arranque crea el esquema desde los
    modelos: si aqui se pierde, una instalacion nueva vuelve a quedar rota.
    """

    def test_every_foreign_key_is_deferrable(self):
        no_diferibles = [
            f"{tabla.name}.{restriccion.name or [c.name for c in restriccion.columns]}"
            for tabla in Base.metadata.tables.values()
            for restriccion in tabla.foreign_key_constraints
            if not restriccion.deferrable
        ]

        self.assertEqual(
            [], no_diferibles,
            "Una llave foranea no diferible impide sembrar una base nueva: "
            f"{no_diferibles}",
        )

    def test_they_are_checked_immediately_by_default(self):
        """No se difiere por omision: los errores deben salir donde ocurren."""
        diferidas_por_omision = [
            f"{tabla.name}.{restriccion.name}"
            for tabla in Base.metadata.tables.values()
            for restriccion in tabla.foreign_key_constraints
            if str(restriccion.initially or "").upper() == "DEFERRED"
        ]

        self.assertEqual(
            [], diferidas_por_omision,
            "Con INITIALLY DEFERRED los errores de la aplicacion saldrian hasta el "
            f"COMMIT, lejos de donde se provocaron: {diferidas_por_omision}",
        )

    def test_the_cycle_that_forced_this_is_still_there(self):
        """Deja constancia de por que existe esta regla.

        Si algun dia se rompe el circulo -por ejemplo haciendo nulable una de
        las dos columnas-, esta prueba avisa para revisar si el aplazamiento
        sigue haciendo falta.
        """
        permission = Base.metadata.tables["permission"]
        user = Base.metadata.tables["user"]

        self.assertFalse(permission.columns["authorized_by"].nullable)
        self.assertFalse(user.columns["id_permission"].nullable)


if __name__ == "__main__":
    unittest.main()
