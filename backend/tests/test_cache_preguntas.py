"""El cache de preguntas: pensar el SQL una vez, reusarlo en la repeticion.

Se prueba contra `ProveedorDeGuion` para que quede clarisimo que la segunda
llamada NO paso por el "modelo": si pasara, `guion.llamadas` tendria dos
entradas en vez de una.
"""

from __future__ import annotations

import json

from app import crear_app
from bi.llm_provider import ProveedorDeGuion
from bi.schema_extractor import CacheDeEsquema
from conftest import preguntar


def _cliente_con_guion(engine, ajustes, guion_dict):
    proveedor = ProveedorDeGuion(guion=guion_dict)
    app = crear_app(ajustes, engine=engine, proveedor=proveedor)
    app.extensions["bi"]["cache"] = CacheDeEsquema(engine, ajustes)
    return app.test_client(), proveedor


def test_la_segunda_pregunta_identica_no_llama_al_modelo(engine, ajustes, guion):
    cliente, proveedor = _cliente_con_guion(engine, ajustes, guion)

    codigo1, datos1 = preguntar(cliente, "ventas totales")
    codigo2, datos2 = preguntar(cliente, "ventas totales")

    assert codigo1 == 200 and codigo2 == 200
    assert len(proveedor.llamadas) == 1, "la segunda pregunta debio salir del cache"

    assert datos1["meta"]["desde_cache"] is False
    assert datos2["meta"]["desde_cache"] is True
    assert datos2["meta"]["ms_modelo"] == 0
    assert "(cache)" in datos2["meta"]["modelo"]

    # Las filas se re-ejecutaron de verdad, no se cachearon: si la base
    # cambiara entre una llamada y otra, la segunda respuesta lo reflejaria.
    assert datos1["widgets"][0]["filas"] == datos2["widgets"][0]["filas"]


def test_mayusculas_y_espacios_no_rompen_el_acierto(engine, ajustes, guion):
    cliente, proveedor = _cliente_con_guion(engine, ajustes, guion)

    preguntar(cliente, "ventas totales")
    preguntar(cliente, "  VENTAS totales  ")

    assert len(proveedor.llamadas) == 1


def test_una_pregunta_distinta_si_llama_al_modelo(engine, ajustes, guion):
    cliente, proveedor = _cliente_con_guion(engine, ajustes, guion)

    preguntar(cliente, "ventas totales")
    preguntar(cliente, "ventas por mes")

    assert len(proveedor.llamadas) == 2


def test_ttl_en_cero_apaga_el_cache(engine, ajustes, guion):
    ajustes_sin_cache = ajustes.con(ttl_preguntas_s=0)
    cliente, proveedor = _cliente_con_guion(engine, ajustes_sin_cache, guion)

    preguntar(cliente, "ventas totales")
    preguntar(cliente, "ventas totales")

    assert len(proveedor.llamadas) == 2
