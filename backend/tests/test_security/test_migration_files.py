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

        El mismo defecto se encontro dos veces por separado, en esta rama y en
        tny_docs, y se arreglo igual en las dos. Que dos personas tropiecen con
        el mismo mensaje inutil -"immutabledict is not a sequence"- es motivo de
        sobra para fijarlo.
        """
        from scripts.apply_migrations import _ejecutar_sql_crudo

        cursor = MagicMock()
        conexion = MagicMock()
        # `connection` es el proxy del pool; `driver_connection`, el DBAPI de
        # verdad. Se simula esa ruta y no la del proxy porque es la que el
        # codigo usa: el proxy reenvia, pero depender de ese reenvio es
        # depender de un detalle interno de SQLAlchemy.
        conexion.connection.driver_connection.cursor.return_value = cursor

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

    def test_no_migration_aborts_on_the_state_of_a_customer_database(self):
        """Ninguna migracion puede abortar por como esta la base de un cliente.

        Las migraciones se reaplican en CADA arranque del pod y `db-migrate`
        detiene el arranque si una falla. Una comprobacion de "se esperaban N
        filas" deja de ser cierta en cuanto un cliente personaliza su
        instalacion: `20260908100000` exigia 4 o 5 roles base y comala retiro
        tres desde el Gestor -> `Init:Error`, y con `Recreate`, sin API. Ya
        habia pasado igual el 2026-09-23 ("exigir 5 reventaba en cada
        reinicio"). Se vigilan TODAS las migraciones, no solo esa: un
        `RAISE EXCEPTION` aqui es siempre una apuesta sobre datos que el
        cliente puede cambiar. Si algo debe avisar, `RAISE NOTICE`.

        Se ignoran los comentarios `--`: los que cuentan la historia de un
        aborto ya corregido pueden nombrar la sentencia sin ejecutarla.
        """
        con_aborto = []
        for archivo in sorted(MIGRACIONES.glob("*.sql")):
            sin_comentarios = "\n".join(
                linea.split("--", 1)[0]
                for linea in archivo.read_text(encoding="utf-8").splitlines()
            )
            if "RAISE EXCEPTION" in sin_comentarios.upper():
                con_aborto.append(archivo.name)
        self.assertEqual([], con_aborto, "\n" + "\n".join(con_aborto))


if __name__ == "__main__":
    unittest.main()
