"""Quien puede gestionar a quien: altas, ediciones, bajas y reinicio de MFA.

El Gestor de roles y permisos decide SI el actor puede gestionar usuarios:
`scope_create` / `scope_update` / `scope_delete` de la entidad `user`, que las
rutas ya exigen con `require_entity_permission`. Aqui solo van las protecciones
que ningun rol operativo debe poder saltarse, y todas son por ROL o por
identidad, nunca por `user_type` (que describe la cuenta, no da autoridad):

  * el superusuario (bootstrap) lo puede todo y nadie mas lo toca;
  * quien tiene el rol Administrator solo lo gestiona otro Administrator o el
    superusuario (asignar ese rol sigue siendo solo del superusuario, ver
    `_payload_assigns_protected_role` en `routes/user.py`);
  * nadie cambia su propio rol.

Una sola definicion para `routes/user.py` y `routes/auth.py`: antes cada uno
tenia su copia de una jerarquia por tipo de cuenta.
"""
from __future__ import annotations

# Es el mismo rol que `routes/permission.py` trata como protegido.
ADMINISTRATOR_ROLE_ID = 1


def _entero(valor) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def actor_is_administrator(user_data: dict | None) -> bool:
    datos = user_data or {}
    return _entero(datos.get("id_permission") or datos.get("permission_id")) == ADMINISTRATOR_ROLE_ID


def can_manage_user(user_data: dict | None, target_role_id, *, actor_is_bootstrap: bool,
                    target_is_bootstrap: bool) -> bool:
    """Si el actor puede editar, borrar o reiniciar el MFA de ESTE usuario.

    No mira si tiene `user` en el Gestor: eso ya lo resolvio la ruta.
    """
    if actor_is_bootstrap:
        return True
    if target_is_bootstrap:
        return False
    if _entero(target_role_id) == ADMINISTRATOR_ROLE_ID:
        return actor_is_administrator(user_data)
    return True


def changes_own_role(user_data: dict | None, target: dict | None, payload: dict | None) -> bool:
    """El actor intenta quedarse con otro rol que el que ya tiene (autoescalada)."""
    if not payload or "id_permission" not in payload or not target:
        return False
    datos = user_data or {}
    if _entero(datos.get("id_user")) != _entero(target.get("id_user")):
        return False
    return _entero(payload.get("id_permission")) != _entero(target.get("id_permission"))
