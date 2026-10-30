"""Revisa un Secret de Kubernetes ANTES de desplegar, con las reglas del arranque.

Por que existe: la guarda de arranque (`app/utils/startup_guard.py`) detiene el
backend en produccion si falta un secreto fuerte. Detectarlo dentro del pod es
detectarlo tarde -- el backend lleva volumen y se despliega con `Recreate`, asi
que el pod viejo ya murio y la API queda caida. Aqui se aplican exactamente las
mismas reglas (una sola fuente) sobre el Secret, sin tocar el clúster.

Uso (solo lectura; no imprime valores):

    kubectl -n adser-prod get secret app-secrets -o json \
        | python backend/scripts/preflight_secrets.py

Sale con codigo 1 si hay algo que HARIA FALLAR el arranque en produccion; los
avisos no cambian el codigo de salida.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.startup_guard import (  # noqa: E402
    collect_configuration_problems,
    collect_configuration_warnings,
)


def entorno_del_secret(documento: dict) -> dict[str, str]:
    datos = documento.get("data") or {}
    return {nombre: base64.b64decode(valor).decode("utf-8", "replace")
            for nombre, valor in datos.items()}


def main() -> int:
    entorno = entorno_del_secret(json.load(sys.stdin))
    problemas = collect_configuration_problems(entorno)
    avisos = collect_configuration_warnings(entorno)
    for problema in problemas:
        print(f"BLOQUEA EL ARRANQUE: {problema}")
    for aviso in avisos:
        print(f"aviso: {aviso}")
    if not problemas:
        print("OK: el Secret no impide el arranque en produccion.")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
