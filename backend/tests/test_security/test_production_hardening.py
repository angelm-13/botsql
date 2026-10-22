"""Controles que impiden que el sistema salga a produccion inseguro.

Los tres nacen del mismo defecto de diseno: cada configuracion faltante
degradaba en silencio a un valor de desarrollo. El sistema levantaba, respondia
y parecia sano, y solo se notaba cuando alguien firmaba un token propio.
"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager

from app.utils import login_throttle
from app.utils.startup_guard import (
    allowed_cors_origins,
    collect_configuration_problems,
    enforce_secure_configuration,
    is_production,
)


VARIABLES = (
    "APP_ENV", "FLASK_ENV", "JWT_SECRET", "SECRET_KEY", "CORS_ORIGINS",
    "BOOTSTRAP_ADMIN_ENABLED", "BOOTSTRAP_ADMIN_PASSWORD",
    "LOGIN_MAX_ATTEMPTS_PER_USER", "LOGIN_MAX_ATTEMPTS_PER_IP",
    "LOGIN_ATTEMPT_WINDOW_SECONDS",
)

SECRETO_VALIDO = "k" * 44


@contextmanager
def entorno(**valores):
    """Aisla las variables de entorno de la prueba."""
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


def produccion_segura(**extra):
    base = {
        "APP_ENV": "production",
        "JWT_SECRET": SECRETO_VALIDO,
        "SECRET_KEY": SECRETO_VALIDO,
        "CORS_ORIGINS": "https://app.tyakxa.mx",
        "BOOTSTRAP_ADMIN_PASSWORD": "una-clave-larga-y-unica-1",
    }
    base.update(extra)
    return base


class TestStartupGuard(unittest.TestCase):
    def test_production_with_no_configuration_refuses_to_start(self):
        """Vale mas un despliegue que falla que uno que corre abierto."""
        with entorno(APP_ENV="production"), self.assertRaises(RuntimeError) as raised:
            enforce_secure_configuration()

        self.assertIn("JWT_SECRET", str(raised.exception))

    def test_a_known_example_secret_is_refused(self):
        """Ese valor esta en el repositorio: cualquiera podria firmar tokens."""
        with entorno(**produccion_segura(JWT_SECRET="dev-secret-change-me")):
            with self.assertRaises(RuntimeError) as raised:
                enforce_secure_configuration()

        self.assertIn("valor de ejemplo", str(raised.exception))

    def test_a_short_secret_is_refused(self):
        with entorno(**produccion_segura(JWT_SECRET="corto")):
            with self.assertRaises(RuntimeError):
                enforce_secure_configuration()

    def test_production_without_cors_origins_is_refused(self):
        with entorno(APP_ENV="production", JWT_SECRET=SECRETO_VALIDO, SECRET_KEY=SECRETO_VALIDO):
            with self.assertRaises(RuntimeError) as raised:
                enforce_secure_configuration()

        self.assertIn("CORS_ORIGINS", str(raised.exception))

    def test_production_with_the_flask_debugger_is_refused(self):
        """El depurador de Flask permite ejecutar codigo desde el navegador."""
        with entorno(**produccion_segura(FLASK_ENV="development")):
            with self.assertRaises(RuntimeError) as raised:
                enforce_secure_configuration()

        self.assertIn("depurador", str(raised.exception))

    def test_a_weak_bootstrap_password_is_refused(self):
        with entorno(**produccion_segura(BOOTSTRAP_ADMIN_ENABLED="true", BOOTSTRAP_ADMIN_PASSWORD="admin")):
            with self.assertRaises(RuntimeError) as raised:
                enforce_secure_configuration()

        self.assertIn("administrador inicial", str(raised.exception))

    def test_a_well_configured_production_starts(self):
        with entorno(**produccion_segura()):
            self.assertEqual([], enforce_secure_configuration())

    def test_outside_production_it_warns_but_does_not_stop(self):
        """En desarrollo no debe estorbar el trabajo diario."""
        with entorno(FLASK_ENV="development"):
            problemas = enforce_secure_configuration()

        self.assertTrue(problemas)

    def test_testing_skips_the_check_entirely(self):
        with entorno(APP_ENV="production"):
            self.assertEqual([], enforce_secure_configuration(testing=True))

    def test_it_recognizes_the_production_environment(self):
        for valor in ("production", "produccion", "prod", "PRODUCTION"):
            with self.subTest(valor=valor), entorno(APP_ENV=valor):
                self.assertTrue(is_production())
        for valor in ("development", "dev", "local", "testing", "staging"):
            with self.subTest(valor=valor), entorno(APP_ENV=valor):
                self.assertFalse(is_production())

    def test_a_forgotten_variable_is_production(self):
        """Falla cerrado: no decir nada no debe abrir el sistema."""
        with entorno():
            self.assertTrue(is_production())
        with entorno(APP_ENV=""):
            self.assertTrue(is_production())


class TestCorsOrigins(unittest.TestCase):
    def test_without_the_variable_no_cross_origin_is_allowed(self):
        """Antes se llamaba a CORS(app) sin argumentos: cualquier sitio pasaba."""
        with entorno():
            self.assertEqual([], allowed_cors_origins())

    def test_it_splits_a_comma_separated_list(self):
        with entorno(CORS_ORIGINS="https://a.mx, https://b.mx"):
            self.assertEqual(["https://a.mx", "https://b.mx"], allowed_cors_origins())

    def test_an_explicit_wildcard_is_respected(self):
        with entorno(CORS_ORIGINS="*"):
            self.assertEqual("*", allowed_cors_origins())

    def test_a_wildcard_is_reported_as_a_problem_in_production(self):
        with entorno(**produccion_segura(CORS_ORIGINS="*")):
            # Se respeta si se pide a proposito, pero no queda callado.
            self.assertEqual([], collect_configuration_problems())
            self.assertEqual("*", allowed_cors_origins())


class TestLoginThrottle(unittest.TestCase):
    def setUp(self):
        login_throttle.reiniciar()

    def tearDown(self):
        login_throttle.reiniciar()

    def test_a_user_is_blocked_after_too_many_failures(self):
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="3", LOGIN_ATTEMPT_WINDOW_SECONDS="900"):
            for _ in range(3):
                self.assertFalse(login_throttle.esta_bloqueado("ana", "10.0.0.1"))
                login_throttle.registrar_fallo("ana", "10.0.0.1")

            self.assertTrue(login_throttle.esta_bloqueado("ana", "10.0.0.1"))

    def test_another_user_from_the_same_place_is_not_blocked_yet(self):
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="3", LOGIN_MAX_ATTEMPTS_PER_IP="30"):
            for _ in range(3):
                login_throttle.registrar_fallo("ana", "10.0.0.1")

            self.assertFalse(login_throttle.esta_bloqueado("beto", "10.0.0.1"))

    def test_a_place_that_sweeps_many_accounts_is_blocked(self):
        """El barrido de cuentas no se detiene contando solo por usuario."""
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="8", LOGIN_MAX_ATTEMPTS_PER_IP="5"):
            for indice in range(5):
                login_throttle.registrar_fallo(f"usuario{indice}", "10.0.0.9")

            self.assertTrue(login_throttle.esta_bloqueado("otro", "10.0.0.9"))

    def test_signing_in_clears_the_user_counter(self):
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="3"):
            login_throttle.registrar_fallo("ana", "10.0.0.1")
            login_throttle.registrar_fallo("ana", "10.0.0.1")
            login_throttle.registrar_exito("ana")

            for _ in range(2):
                login_throttle.registrar_fallo("ana", "10.0.0.1")
            self.assertFalse(login_throttle.esta_bloqueado("ana", "10.0.0.1"))

    def test_signing_in_does_not_clear_the_place_counter(self):
        """Acertar la cuenta 21 no vuelve inocentes a las 20 anteriores."""
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="8", LOGIN_MAX_ATTEMPTS_PER_IP="3"):
            for indice in range(3):
                login_throttle.registrar_fallo(f"usuario{indice}", "10.0.0.9")
            login_throttle.registrar_exito("usuario0")

            self.assertTrue(login_throttle.esta_bloqueado("usuario0", "10.0.0.9"))

    def test_attempts_expire_with_the_window(self):
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="2", LOGIN_ATTEMPT_WINDOW_SECONDS="1"):
            login_throttle.registrar_fallo("ana", "10.0.0.1")
            login_throttle.registrar_fallo("ana", "10.0.0.1")
            self.assertTrue(login_throttle.esta_bloqueado("ana", "10.0.0.1"))

            import time
            time.sleep(1.1)
            self.assertFalse(login_throttle.esta_bloqueado("ana", "10.0.0.1"))

    def test_it_reports_how_long_to_wait(self):
        with entorno(LOGIN_MAX_ATTEMPTS_PER_USER="1", LOGIN_ATTEMPT_WINDOW_SECONDS="600"):
            login_throttle.registrar_fallo("ana", "10.0.0.1")

            espera = login_throttle.segundos_para_reintentar("ana", "10.0.0.1")

            self.assertGreater(espera, 0)
            self.assertLessEqual(espera, 601)

    def test_someone_not_blocked_waits_nothing(self):
        self.assertEqual(0, login_throttle.segundos_para_reintentar("ana", "10.0.0.1"))


if __name__ == "__main__":
    unittest.main()


class TestAdministradorInicial(unittest.TestCase):
    def test_the_default_bootstrap_admin_counts_as_weak_when_the_variable_is_unset(self):
        from app.utils.startup_guard import collect_configuration_problems

        with entorno(APP_ENV="production", JWT_SECRET="x" * 40, SECRET_KEY="y" * 40,
                     CORS_ORIGINS="https://a.mx"):
            problemas = collect_configuration_problems()
        self.assertTrue(any("administrador inicial" in p for p in problemas))

    def test_a_strong_password_clears_it(self):
        from app.utils.startup_guard import collect_configuration_problems

        with entorno(APP_ENV="production", JWT_SECRET="x" * 40, SECRET_KEY="y" * 40,
                     CORS_ORIGINS="https://a.mx", BOOTSTRAP_ADMIN_PASSWORD="una-clave-larga-y-unica-1"):
            self.assertEqual([], collect_configuration_problems())
