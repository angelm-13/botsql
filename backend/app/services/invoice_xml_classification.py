from __future__ import annotations

import re


def normalize_rfc(value) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").strip().upper())


def classify_invoice_direction(principal_rfc, issuer_rfc, receiver_rfc) -> str:
    principal = normalize_rfc(principal_rfc)
    issuer = normalize_rfc(issuer_rfc)
    receiver = normalize_rfc(receiver_rfc)
    if not principal or (issuer == principal and receiver == principal):
        return "sin_clasificar"
    if issuer == principal:
        return "venta"
    if receiver == principal:
        return "compra"
    return "sin_clasificar"