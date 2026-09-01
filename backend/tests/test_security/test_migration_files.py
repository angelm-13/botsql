"""Que las migraciones puedan siquiera ejecutarse.

No comprueban que el SQL sea correcto -para eso esta aplicarlo- sino que el
archivo llegue al servidor. La diferencia importa: `entrypoint.sh` detiene el
arranque si una migracion falla, a proposito, asi que un archivo que el
aplicador no puede mandar deja la aplicacion caida sin levantar nunca.
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import MagicMock

RAIZ = pathlib.Path(__file__).resolve().parents[3]
MIGRACIONES = RAIZ / "database" / "migrations"
sys.path.insert(0, str(RAIZ / "backend"))


class TestArchivosDeMigracion(unittest.TestCase):

    def test_migrations_directory_is_where_expected(self):
        """Si el directorio se mueve, las demas pruebas pasarian vacias."""
        self.assertTrue(MIGRACIONES.is_dir(), f"no existe {MIGRACIONES}")
        self.assertGreater(len(list(MIGRACIONES.glob("*.sql"))), 10)

    def test_the_applier_does_not_interpolate_parameters(self):
        """Un porcentaje en el archivo no puede tumbar la migracion.

        `exec_driver_sql` pasa un diccionario vacio de parametros y con eso
        psycopg2 recorre todo el texto buscando marcadores, sin distinguir
        codigo de comentario. Un solo `%` sin duplicar hacia fallar el archivo
        entero con "immutabledict is not a sequence", un mensaje que no menciona
        el porcentaje y manda a buscar el problema donde no esta.

        Dos migraciones ya escritas caian en esto: una base nueva se detenia en
        la primera y el servidor nunca arrancaba.

        Lo que se fija aqui es que el SQL viaje por `cursor.execute(sql)` con un
        solo argumento. Con dos -aunque el segundo este vacio- psycopg2
        interpola, y volvemos al principio.
        """
        from scripts.apply_migrations import _ejecutar_sql_crudo

        cursor = MagicMock()
        conexion = MagicMock()
        conexion.connection.cursor.return_value = cursor

        sql = "-- un comentario con % dentro\nSELECT 1 WHERE 'abc' LIKE 'a%';"
        _ejecutar_sql_crudo(conexion, sql)

        cursor.execute.assert_called_once_with(sql)
        self.assertEqual(
            1, len(cursor.execute.call_args.args),
            "el SQL debe ir solo; un segundo argumento reactiva la interpolacion",
        )
        cursor.close.assert_called_once()

    def test_every_migration_reads_as_text(self):
        """Un archivo que no se puede leer detiene el arranque igual que uno roto."""
        ilegibles = []
        for archivo in sorted(MIGRACIONES.glob("*.sql")):
            try:
                if not archivo.read_text(encoding="utf-8").strip():
                    ilegibles.append(f"{archivo.name}: vacio")
            except UnicodeDecodeError as error:
                ilegibles.append(f"{archivo.name}: {error}")
        self.assertEqual([], ilegibles, "\n" + "\n".join(ilegibles))


if __name__ == "__main__":
    unittest.main()
