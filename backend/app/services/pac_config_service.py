from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.models.pac_config import PacConfig
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError


VALID_PROVIDERS = {"fake", "facturama_sandbox", "facturama"}


def default_base_url(provider: str) -> str:
    return "https://api.facturama.mx" if provider == "facturama" else "https://apisandbox.facturama.mx"


def _encryption_key() -> bytes:
    source = os.getenv("PAC_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or SECRET_KEY
    return hashlib.sha256(str(source).encode("utf-8")).digest()


def encrypt_password(password: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    cipher = AESGCM(_encryption_key()).encrypt(nonce, password.encode("utf-8"), None)
    return cipher, nonce


def decrypt_password(config: PacConfig | None) -> str:
    if not config or not config.facturama_password_cipher or not config.facturama_password_nonce:
        return ""
    return AESGCM(_encryption_key()).decrypt(
        bytes(config.facturama_password_nonce), bytes(config.facturama_password_cipher), None
    ).decode("utf-8")


def get_config() -> dict:
    with transaction_context() as db:
        config = db.get(PacConfig, 1)
        return config.serialize() if config else PacConfig().serialize()


def save_config(payload: dict) -> dict:
    provider = str(payload.get("provider") or "fake").strip().lower()
    if provider not in VALID_PROVIDERS:
        raise AppError("stamping.provider_invalid", 400, {"allowed": sorted(VALID_PROVIDERS)})
    # La URL siempre es la canonica del provider elegido, nunca la que mande
    # el admin: la pantalla de configuracion no debe poder mostrar (ni guardar)
    # un base_url que no coincida con el modo real (prod/sandbox).
    base_url = default_base_url(provider)
    expedition_place = str(payload.get("expedition_place") or "").strip()
    if expedition_place and (len(expedition_place) != 5 or not expedition_place.isdigit()):
        raise AppError("stamping.expedition_place_invalid", 400, {"field": "expedition_place"})

    with transaction_context() as db:
        config = db.get(PacConfig, 1) or PacConfig(id_pac_config=1)
        config.provider = provider
        config.facturama_username = str(payload.get("facturama_username") or "").strip() or None
        config.facturama_base_url = base_url if provider != "fake" else None
        config.expedition_place = expedition_place or None
        config.name_id = str(payload.get("name_id") or "1").strip() or "1"
        password = str(payload.get("facturama_password") or "")
        if password:
            config.facturama_password_cipher, config.facturama_password_nonce = encrypt_password(password)
        db.add(config)
        db.flush()
        return config.serialize()


def provider_credentials(override: dict | None = None) -> dict:
    override = override or {}
    with transaction_context() as db:
        config = db.get(PacConfig, 1)
        provider = str(override.get("provider") or (config.provider if config else os.getenv("STAMPING_PROVIDER", "fake"))).strip().lower()
        return {
            "provider": provider,
            "username": str(override.get("facturama_username") or (config.facturama_username if config else "") or os.getenv("FACTURAMA_USERNAME") or os.getenv("FACTURAMA_USER") or ""),
            "password": str(override.get("facturama_password") or decrypt_password(config) or os.getenv("FACTURAMA_PASSWORD") or os.getenv("FACTURAMA_PASS") or ""),
            # Siempre la canonica del provider resuelto -- ni el override ni lo
            # guardado en config pueden desviar a que un modo "sandbox" termine
            # pegandole a produccion o viceversa.
            "base_url": default_base_url(provider),
            "expedition_place": str(override.get("expedition_place") or (config.expedition_place if config else "") or ""),
            "name_id": str(override.get("name_id") or (config.name_id if config else "1") or "1"),
        }