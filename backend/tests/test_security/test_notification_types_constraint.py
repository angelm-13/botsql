"""La restriccion de tipos de notificacion tiene UNA sola dueña.

Las migraciones se reaplican todas en cada arranque. Si varias recrean
`notification_type_check`, cada una con su lista, una VIEJA vuelve a poner una lista
mas corta que las filas que ya existen y el `ADD CONSTRAINT` falla; con `set -e` +
`ON_ERROR_STOP=1` el backend no arranca. Es el mismo defecto que ya tumbo
`proyect_event_event_type_check`.

Y un tipo que el codigo escribe y la restriccion no conoce hace reventar
`create_notification` en silencio (el aviso es "best effort"): la campana nunca lo
muestra y nadie ve el error. Las pruebas con SQLite no lo detectan, porque ahi no
existe la restriccion.
"""

from __future__ import annotations

import pathlib
import re
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[3]
MIGRACIONES = RAIZ / "database" / "migrations"
APP = RAIZ / "backend" / "app"


def _migraciones_que_la_recrean():
    return sorted(
        p for p in MIGRACIONES.glob("*.sql")
        if re.search(r"ADD\s+CONSTRAINT\s+notification_type_check",
                     p.read_text(encoding="utf-8"), re.IGNORECASE))


def _tipos_permitidos(sql: str) -> set[str]:
    bloque = re.search(r"notification_type\s+IN\s*\((.*?)\)\s*\)", sql, re.S | re.IGNORECASE)
    return set(re.findall(r"'([a-z_]+)'", bloque.group(1))) if bloque else set()


class TestTiposDeNotificacion(unittest.TestCase):

    def test_exactly_one_migration_owns_the_constraint(self):
        duenas = _migraciones_que_la_recrean()
        self.assertEqual(
            1, len(duenas),
            "notification_type_check la recrean %s: debe haber UNA sola migracion, la "
            "mas nueva, con la lista completa" % [p.name for p in duenas])

    def test_the_owner_is_the_newest_migration_that_touches_it(self):
        """Corre ultima en cada arranque, asi que su lista es la que queda."""
        duena = _migraciones_que_la_recrean()[0]
        tocan = sorted(p for p in MIGRACIONES.glob("*.sql")
                       if "notification_type_check" in p.read_text(encoding="utf-8"))
        self.assertEqual(tocan[-1].name, duena.name)

    def test_every_type_the_code_writes_is_allowed(self):
        permitidos = _tipos_permitidos(_migraciones_que_la_recrean()[0].read_text(encoding="utf-8"))
        self.assertTrue(permitidos, "no se pudo leer la lista de tipos permitidos")

        usados = set()
        for archivo in APP.rglob("*.py"):
            usados |= set(re.findall(r'notification_type\s*=\s*"([a-z_]+)"',
                                     archivo.read_text(encoding="utf-8")))
        # Los avisos de compras eligen el tipo desde una tabla, no con un literal.
        from app.services.purchase_order_service import _AVISOS
        usados |= {tipo for tipo, _ in _AVISOS.values()}

        faltan = usados - permitidos
        self.assertEqual(set(), faltan,
                         "el codigo escribe tipos que la restriccion rechaza: %s" % sorted(faltan))
