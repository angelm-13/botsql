from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.exportar_catalogo_kpis import RUTA_DEL_FIXTURE, catalogo_del_registry

# El selector de KPI del Dashboard se prueba en node (frontend/src/kpi/*.test.*) contra una COPIA de
# los KPIs de KPI_REGISTRY: node no puede importar Python. Si el registry cambia y la copia no, esas
# pruebas siguen en verde contra un catalogo que ya no existe. Esta prueba es lo que lo impide.
#
# Donde esta la copia: en el repo, <raiz>/backend/tests/test_services/ -> parents[3] es la raiz. Dentro
# del contenedor del backend (que solo ve ./backend) la raiz es `/` y docker-compose.yml monta
# ./frontend/src/kpi/fixtures en /frontend/src/kpi/fixtures, de solo lectura (mismo patron que
# ./database -> /database para las pruebas de migraciones).
#
# Si la CARPETA no esta (un contenedor creado antes del montaje, o una copia del backend sin el frontend),
# las pruebas que comparan se SALTAN con un mensaje que dice por que: no hay nada que comparar y eso no es un
# defecto del codigo. Si la carpeta esta pero el archivo no, FALLA: alguien lo movio o lo borro.
RAIZ = Path(__file__).resolve().parents[3]
FIXTURE = RAIZ / RUTA_DEL_FIXTURE
CARPETA_DEL_FIXTURE = FIXTURE.parent

MENSAJE_SIN_MONTAJE = (
    f"SALTADA, no verificada: no hay {CARPETA_DEL_FIXTURE}, asi que no se pudo comparar el catalogo del frontend con "
    "KPI_REGISTRY. En el repo esa carpeta siempre existe; dentro del contenedor del backend la pone el montaje "
    "`./frontend/src/kpi/fixtures:/frontend/src/kpi/fixtures:ro` de docker-compose.yml. Si es un contenedor creado "
    "antes de ese montaje, recrealo (`docker compose up -d backend`); ver docs/despliegues/"
    "2026-10-16_montaje_de_fixtures_de_kpi_en_el_compose.md."
)

MENSAJE_SIN_ARCHIVO = (
    f"Existe {CARPETA_DEL_FIXTURE} pero no {FIXTURE.name}: alguien lo movio o lo borro. Se regenera con "
    "scripts/exportar_catalogo_kpis.py (el comando esta en su cabecera)."
)

COMO_ACTUALIZAR = (
    "Para actualizarlo, desde la raiz del repo:\n"
    "    docker compose run --rm --no-deps -T --entrypoint python backend \\\n"
    "        scripts/exportar_catalogo_kpis.py > /tmp/catalogo_del_registry.json \\\n"
    f"        && mv /tmp/catalogo_del_registry.json {RUTA_DEL_FIXTURE.as_posix()}\n"
    "y despues corre las pruebas del front (cd frontend && node --test --test-concurrency=1 src/kpi/): un KPI nuevo\n"
    "puede cambiar los conteos que fijan (pestanas, tarjetas, \"Variables\"). Detalle en scripts/exportar_catalogo_kpis.py."
)


def _diferencias(fixture: list[dict], registry: list[dict]) -> list[str]:
    """Que cambio, KPI por KPI, para que el mensaje diga que actualizar y no solo que algo no coincide."""
    en_fixture = {fila["clave"]: fila for fila in fixture}
    en_registry = {fila["clave"]: fila for fila in registry}
    lineas = []
    for clave in en_registry.keys() - en_fixture.keys():
        lineas.append(f"  + {clave}: esta en KPI_REGISTRY y falta en el fixture")
    for clave in en_fixture.keys() - en_registry.keys():
        lineas.append(f"  - {clave}: esta en el fixture y ya no existe en KPI_REGISTRY")
    for clave in en_registry.keys() & en_fixture.keys():
        for campo in sorted(en_registry[clave].keys() | en_fixture[clave].keys()):
            if en_fixture[clave].get(campo) != en_registry[clave].get(campo):
                lineas.append(
                    f"  ~ {clave}.{campo}: fixture={en_fixture[clave].get(campo)!r} registry={en_registry[clave].get(campo)!r}"
                )
    return sorted(lineas)


class CatalogoDelRegistryTest(unittest.TestCase):
    def setUp(self):
        if not CARPETA_DEL_FIXTURE.is_dir():
            self.skipTest(MENSAJE_SIN_MONTAJE)

    def test_el_fixture_esta_donde_se_espera(self):
        # La carpeta esta (si no, setUp salto la prueba): que el archivo no falte, para que la comparacion de abajo
        # no pase vacia.
        self.assertTrue(FIXTURE.is_file(), MENSAJE_SIN_ARCHIVO)

    def test_el_fixture_del_frontend_coincide_con_kpi_registry(self):
        self.assertTrue(FIXTURE.is_file(), MENSAJE_SIN_ARCHIVO)
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        registry = catalogo_del_registry()
        if fixture == registry:
            return
        diferencias = _diferencias(fixture, registry)
        if not diferencias:
            # Mismas filas pero distinto orden o distintos ids: el selector agrupa y cuenta en el orden del registry.
            diferencias = ["  ~ mismas filas, pero en otro orden o con otros id_kpi_definition (el id es la posicion en KPI_REGISTRY)"]
        self.fail(
            f"{RUTA_DEL_FIXTURE.as_posix()} esta desfasado respecto de KPI_REGISTRY "
            f"(fixture: {len(fixture)} KPIs, registry: {len(registry)}):\n"
            + "\n".join(diferencias)
            + "\n\n"
            + COMO_ACTUALIZAR
        )


class CatalogoExportadoTest(unittest.TestCase):
    """No necesita el fixture: corre siempre, tambien en un contenedor sin el montaje."""

    def test_el_catalogo_exportado_son_los_campos_que_el_frontend_lee(self):
        # Si se agrega o se quita un campo aqui, el fixture y las pruebas del front deben enterarse a proposito.
        for fila in catalogo_del_registry():
            self.assertEqual(
                ["id_kpi_definition", "clave", "etiqueta", "modulo", "dimensiones", "unidad", "modo"], list(fila), fila["clave"],
            )


if __name__ == "__main__":
    unittest.main()
