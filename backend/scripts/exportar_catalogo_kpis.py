"""Exporta el catalogo de KPIs del registry con la forma que usan las pruebas del frontend.

Por que existe
--------------
`frontend/src/kpi/fixtures/catalogo_del_registry.json` es una copia de los KPIs de
`KPI_REGISTRY` (`app/kpis/registry.py`): las pruebas del selector del Dashboard
(`selectorAgrupamiento.test.js`, `renderSelector.test.mjs`) corren en node y no pueden
importar Python. Un KPI nuevo, o uno que cambia de modulo, de unidad o de nombre, deja la
copia desfasada y esas pruebas siguen en verde contra un catalogo que ya no existe.

`tests/test_services/test_kpi_catalogo_del_registry.py` compara la copia con el registry
y falla si no coinciden; esta es la UNICA forma de producirla, para que la prueba y quien
la regenera hablen de lo mismo (`catalogo_del_registry` y `serializar`).

Que hace
--------
Imprime el JSON en la salida estandar: no escribe ningun archivo ni toca la base. Una fila
por KPI, en el orden del registry; `id_kpi_definition` es la posicion (1, 2, ...), que es
el id que daria una base sembrada desde cero, no el de ningun ambiente real.

Como regenerar la copia (desde la raiz del repo; el montaje del fixture en el contenedor es
de solo lectura a proposito, por eso la salida se redirige en el host):

    docker compose run --rm --no-deps -T --entrypoint python backend \\
        scripts/exportar_catalogo_kpis.py > /tmp/catalogo_del_registry.json \\
        && mv /tmp/catalogo_del_registry.json frontend/src/kpi/fixtures/catalogo_del_registry.json

Despues, correr las pruebas del front (`cd frontend && node --test --test-concurrency=1 src/kpi/`):
un KPI nuevo puede cambiar los conteos que esas pruebas fijan (pestanas, tarjetas, "Variables").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.kpis.registry import KPI_REGISTRY  # noqa: E402

# Ruta del fixture respecto de la raiz del repo, para los mensajes y para la prueba.
RUTA_DEL_FIXTURE = Path("frontend") / "src" / "kpi" / "fixtures" / "catalogo_del_registry.json"


def catalogo_del_registry() -> list[dict]:
    """Los KPIs del registry, en su orden, con los campos que el frontend lee del catalogo."""
    return [
        {
            "id_kpi_definition": posicion,
            "clave": kpi.clave,
            "etiqueta": kpi.etiqueta,
            "modulo": kpi.modulo,
            "grupo": kpi.grupo,
            "dimensiones": list(kpi.dimensiones),
            "unidad": kpi.unidad,
            "modo": kpi.modo,
        }
        for posicion, kpi in enumerate(KPI_REGISTRY, start=1)
    ]


def serializar(catalogo: list[dict]) -> str:
    """El texto exacto del fixture: sangria de 1 espacio, sin escapar acentos, con salto final."""
    return json.dumps(catalogo, indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    sys.stdout.write(serializar(catalogo_del_registry()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
