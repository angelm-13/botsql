"""Trampas conocidas de los archivos de migracion.

No comprueban que el SQL sea correcto -para eso esta aplicarlo- sino que el
archivo pueda siquiera ejecutarse. La diferencia importa: una migracion que
falla al aplicarse detiene el arranque del servidor, y el aplicador esta hecho
para eso a proposito, asi que un archivo mal formado deja la aplicacion caida.
"""

from __future__ import annotations

import pathlib
import unittest


MIGRACIONES = pathlib.Path(__file__).resolve().parents[3] / "database" / "migrations"


class TestArchivosDeMigracion(unittest.TestCase):

    def test_migrations_directory_is_where_expected(self):
        """Si el directorio se mueve, esta prueba pasaria vacia sin avisar."""
        self.assertTrue(MIGRACIONES.is_dir(), f"no existe {MIGRACIONES}")
        self.assertGreater(len(list(MIGRACIONES.glob("*.sql"))), 10)

    def test_no_migration_contains_a_percent_sign(self):
        """El signo de porcentaje tumba la migracion, incluso en un comentario.

        `apply_migrations.py` manda el archivo completo por `exec_driver_sql`, y
        el driver busca marcadores de parametro en todo el texto sin distinguir
        que es codigo y que es comentario. Un solo `%` -en un LIKE, en un
        `to_char`, o en una linea que explica algo- hace fallar la migracion con
        "immutabledict is not a sequence", que no menciona el porcentaje por
        ningun lado y manda a buscar el problema donde no esta.

        Se comprobo caso por caso contra el driver real: un LIKE con comodin,
        un `RAISE NOTICE` dentro de un bloque DO y un porcentaje suelto en un
        comentario fallan los tres; duplicado no falla. La regla es entonces
        "duplicado o nada".

        Esto no es hipotetico: dos migraciones ya registradas como aplicadas no
        podian ejecutarse por esta causa, asi que una base nueva se detenia en
        la primera de ellas y el servidor nunca arrancaba. Se corrigieron
        duplicando el porcentaje, que produce exactamente el mismo SQL en
        Postgres.
        """
        culpables = []
        for archivo in sorted(MIGRACIONES.glob("*.sql")):
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            for numero, linea in enumerate(texto.splitlines(), 1):
                if "%" in linea and "%%" not in linea:
                    culpables.append(f"{archivo.name}:{numero}: {linea.strip()[:90]}")
        self.assertEqual([], culpables, "\n" + "\n".join(culpables))


if __name__ == "__main__":
    unittest.main()
