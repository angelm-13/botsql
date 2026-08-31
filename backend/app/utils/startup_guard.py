"""Comprobaciones de arranque para que produccion no salga insegura.

El sistema estaba escrito de modo que cada configuracion faltante degradaba en
silencio a un valor de desarrollo: sin `JWT_SECRET` firmaba los tokens con
`dev-secret-change-me`, que esta en el codigo y cualquiera puede leer; sin
`FLASK_ENV` arrancaba con el depurador de Flask expuesto, que permite ejecutar
codigo desde el navegador; y sin `CORS_ORIGINS` aceptaba peticiones de
cualquier sitio.

Ninguna de esas fallas avisa. El sistema levanta, responde y parece sano, y
solo se nota cuando alguien firma un token propio.

Aqui se invierte esa logica: en produccion, una configuracion insegura impide
arrancar. Vale mas un despliegue que falla ruidosamente que uno que corre
abierto sin que nadie lo sepa. En desarrollo se avisa por bitacora y se sigue,
para no estorbar el trabajo diario.
"""

from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)

# Secretos que el codigo trae como valor de reserva. Si alguno sobrevive hasta
# produccion, los tokens son falsificables por cualquiera que lea el
# repositorio.
INSECURE_SECRETS = {
    "dev-secret-change-me",
    "change-me",
    "change-me-legacy-jwt-secret",
    "secret",
    "changeme",
}

# Variables sin las cuales no se puede considerar segura una instalacion.
REQUIRED_SECRETS = ("JWT_SECRET", "SECRET_KEY")

PRODUCTION_ENVIRONMENTS = {"production", "produccion", "prod"}


def is_production() -> bool:
    entorno = str(os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "").strip().lower()
    return entorno in PRODUCTION_ENVIRONMENTS


def collect_configuration_problems() -> list[str]:
    """Problemas de configuracion que harian insegura la instalacion."""
    problemas: list[str] = []

    for variable in REQUIRED_SECRETS:
        valor = str(os.getenv(variable) or "").strip()
        if not valor:
            problemas.append(f"{variable} no esta definida; se usaria un secreto de desarrollo publico.")
        elif valor.lower() in INSECURE_SECRETS:
            problemas.append(f"{variable} conserva un valor de ejemplo conocido.")
        elif len(valor) < 32:
            # Una firma HS256 con menos de 32 caracteres es debil frente a
            # fuerza bruta sobre un token capturado.
            problemas.append(f"{variable} es demasiado corta: usa al menos 32 caracteres.")

    if not str(os.getenv("CORS_ORIGINS") or "").strip():
        problemas.append("CORS_ORIGINS no esta definida; el API aceptaria peticiones de cualquier sitio.")

    if str(os.getenv("FLASK_ENV") or "").strip().lower() == "development":
        problemas.append("FLASK_ENV sigue en development; el arranque expondria el depurador de Flask.")

    if _bootstrap_admin_is_weak():
        problemas.append("La contrasena del administrador inicial es la de ejemplo o esta vacia.")

    return problemas


def _bootstrap_admin_is_weak() -> bool:
    if str(os.getenv("BOOTSTRAP_ADMIN_ENABLED") or "").strip().lower() not in {"1", "true", "yes", "si"}:
        return False
    clave = str(os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
    return not clave or clave.lower() in INSECURE_SECRETS or len(clave) < 12


def enforce_secure_configuration(*, testing: bool = False) -> list[str]:
    """Detiene el arranque en produccion si la configuracion es insegura.

    Devuelve los problemas encontrados. En produccion levanta `RuntimeError`
    antes de que la aplicacion atienda una sola peticion.
    """
    if testing:
        return []

    problemas = collect_configuration_problems()
    if not problemas:
        return []

    if is_production():
        detalle = "\n".join(f"  - {p}" for p in problemas)
        raise RuntimeError(
            "La configuracion no es apta para produccion:\n"
            f"{detalle}\n"
            "Corrige estas variables antes de desplegar."
        )

    for problema in problemas:
        logger.warning("Configuracion insegura (tolerada fuera de produccion): %s", problema)
    return problemas


def allowed_cors_origins() -> list[str] | str:
    """Origenes permitidos.

    Se leen de `CORS_ORIGINS`, separados por comas. Sin esa variable se
    devuelve la lista vacia, que a Flask-CORS le dice que no permita ningun
    origen cruzado: es preferible que el navegador bloquee a que el API quede
    abierto a cualquier sitio.
    """
    crudo = str(os.getenv("CORS_ORIGINS") or "").strip()
    if not crudo:
        return []
    if crudo == "*":
        # Se respeta si alguien lo pide a proposito, pero queda constancia.
        logger.warning("CORS_ORIGINS es '*': el API acepta peticiones de cualquier sitio.")
        return "*"
    return [origen.strip() for origen in crudo.split(",") if origen.strip()]
