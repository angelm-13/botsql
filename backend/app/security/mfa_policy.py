
from __future__ import annotations

HIGH_RISK_ACTIONS = {"delete", "export", "permission_change", "mfa_disable"}


def requires_recent_mfa(action: str) -> bool:
    return action in HIGH_RISK_ACTIONS


def validate_recent_mfa_claims(user_data: dict, max_age_seconds: int = 900) -> bool:
    # El backend de auth debe insertar `mfa_verified_at` en el JWT final.
    return bool(user_data.get("mfa_verified_at"))
