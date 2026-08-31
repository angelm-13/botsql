"""Dos fugas del portal publico, del mismo patron que las del login interno.

Ambas nacen de degradar en silencio cuando falta configuracion: el sistema
sigue respondiendo como si todo fuera bien, y lo que se pierde por el camino no
deja rastro visible.
"""

from __future__ import annotations

import logging
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.routes import public_auth


VARIABLES = ("APP_ENV", "FLASK_ENV", "SMTP_HOST", "MAIL_SERVER", "PUBLIC_FRONTEND_BASE_URL")


@contextmanager
def entorno(**valores):
    previos = {nombre: os.environ.get(nombre) for nombre in VARIABLES}
    for nombre in VARIABLES:
        os.environ.pop(nombre, None)
    os.environ.update({k: v for k, v in valores.items() if v is not None})
    try:
        yield
    finally:
        for nombre in VARIABLES:
            os.environ.pop(nombre, None)
            if previos[nombre] is not None:
                os.environ[nombre] = previos[nombre]


class _AppFalsa:
    """Sustituye a `current_app` para capturar lo que se registra."""

    def __init__(self):
        self.logger = logging.getLogger("prueba.portal")


@contextmanager
def capturar_bitacora():
    app = _AppFalsa()
    with patch.object(public_auth, "current_app", app):
        with unittest.TestCase().assertLogs("prueba.portal", level="DEBUG") as registro:
            yield registro


class TestEnlaceDeRestablecimiento(unittest.TestCase):
    """Sin SMTP, el enlace se imprimia en la salida del proceso.

    Ese enlace vale tanto como la contrasena: quien lo lea entra a la cuenta. En
    un contenedor la salida es la bitacora, y la bitacora suele leerla mas gente
    -y guardarse mas tiempo- de lo que nadie penso al escribir ese `print`.
    """

    def test_in_production_the_link_never_reaches_the_log(self):
        with entorno(APP_ENV="production"), capturar_bitacora() as registro:
            with self.assertRaises(RuntimeError):
                public_auth._send_reset_email("ana@ejemplo.mx", "token-secreto-123")

        completo = "\n".join(registro.output)
        self.assertNotIn("token-secreto-123", completo)
        self.assertIn("SMTP_HOST", completo)

    def test_outside_production_it_still_helps_the_developer(self):
        """En desarrollo no hay buzon donde mirar; ahi si es util."""
        with entorno(FLASK_ENV="development"), capturar_bitacora() as registro:
            public_auth._send_reset_email("ana@ejemplo.mx", "token-secreto-123")

        self.assertIn("token-secreto-123", "\n".join(registro.output))

    def test_the_link_is_built_from_the_configured_frontend(self):
        with entorno(FLASK_ENV="development",
                     PUBLIC_FRONTEND_BASE_URL="https://tienda.tyakxa.mx/"), capturar_bitacora() as registro:
            public_auth._send_reset_email("ana@ejemplo.mx", "abc")

        self.assertIn("https://tienda.tyakxa.mx/reset-password?token=abc",
                      "\n".join(registro.output))


class TestContrasenaDelPortal(unittest.TestCase):
    """El respaldo en texto plano tambien estaba aqui, no solo en el interno."""

    NO_ES_HASH = "contrasena-guardada-en-claro"

    def test_a_correct_bcrypt_password_passes(self):
        cifrada = public_auth._hash_password("Prueba2026!")
        self.assertTrue(public_auth._verify_password("Prueba2026!", cifrada))

    def test_a_wrong_bcrypt_password_fails(self):
        cifrada = public_auth._hash_password("Prueba2026!")
        self.assertFalse(public_auth._verify_password("otra", cifrada))

    def test_in_production_an_unhashed_account_cannot_sign_in(self):
        with entorno(APP_ENV="production"), capturar_bitacora() as registro:
            resultado = public_auth._verify_password(self.NO_ES_HASH, self.NO_ES_HASH)

        self.assertFalse(resultado)
        self.assertIn("sin cifrar", "\n".join(registro.output))

    def test_outside_production_it_is_tolerated_but_recorded(self):
        with entorno(FLASK_ENV="development"), capturar_bitacora() as registro:
            resultado = public_auth._verify_password(self.NO_ES_HASH, self.NO_ES_HASH)

        self.assertTrue(resultado)
        self.assertIn("sin cifrar", "\n".join(registro.output))

    def test_an_empty_password_never_passes(self):
        for clave, guardada in (("", "algo"), ("algo", ""), ("", "")):
            with self.subTest(clave=clave, guardada=guardada):
                self.assertFalse(public_auth._verify_password(clave, guardada))


if __name__ == "__main__":
    unittest.main()
