"""La contrasena de admin1: init.sql la siembra con un hash publico y init_db.py
debe reemplazarlo por BOOTSTRAP_ADMIN_PASSWORD sin pisar el cambio de una persona.

Caso real (comala-prod, 2026-10-12): en una base limpia admin1 quedaba con
"test password" porque "ya hay hash" se leia como un cambio hecho a mano, y el
Secret nunca se aplicaba.
"""
from pathlib import Path

import bcrypt

import init_db
from init_db import (
    DEFAULT_BOOTSTRAP_PASSWORD,
    SEEDED_DEFAULT_HASH,
    password_hash_needs_reset,
)

SECRETO = "Cm-0123456789abcdef-Ax9"


def test_the_seeded_hash_is_the_one_init_sql_writes_for_admin1():
    # En el repo vive en <raiz>/database; dentro del contenedor, montada en /database.
    candidatas = [Path(__file__).resolve().parents[3] / "database" / "init.sql", Path("/database/init.sql")]
    existente = next((c for c in candidatas if c.exists()), None)
    assert existente is not None, "no se encontro database/init.sql"
    assert SEEDED_DEFAULT_HASH in existente.read_text(encoding="utf-8")


def test_the_seeded_hash_is_the_default_password():
    assert bcrypt.checkpw(DEFAULT_BOOTSTRAP_PASSWORD.encode(), SEEDED_DEFAULT_HASH.encode())


def test_the_seeded_default_is_replaced_when_the_secret_defines_a_password():
    assert password_hash_needs_reset(SEEDED_DEFAULT_HASH, SECRETO) is True


def test_an_empty_hash_is_always_restored():
    assert password_hash_needs_reset(None, SECRETO) is True
    assert password_hash_needs_reset("", SECRETO) is True
    assert password_hash_needs_reset("", DEFAULT_BOOTSTRAP_PASSWORD) is True


def test_a_hash_changed_by_a_person_is_never_touched():
    cambiado = bcrypt.hashpw(b"otra contrasena real", bcrypt.gensalt(rounds=4)).decode()
    assert password_hash_needs_reset(cambiado, SECRETO) is False
    assert password_hash_needs_reset(cambiado, DEFAULT_BOOTSTRAP_PASSWORD) is False


def test_without_a_configured_secret_the_seeded_default_is_left_alone():
    # Reemplazarlo por el hash de la misma contrasena no cambiaria nada.
    assert password_hash_needs_reset(SEEDED_DEFAULT_HASH, DEFAULT_BOOTSTRAP_PASSWORD) is False


def test_bootstrap_password_falls_back_to_the_documented_default(monkeypatch):
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    assert init_db.bootstrap_admin_password() == DEFAULT_BOOTSTRAP_PASSWORD
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", SECRETO)
    assert init_db.bootstrap_admin_password() == SECRETO
