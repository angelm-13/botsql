"""PASO 2 -- El servidor.

Arranca el modulo de BI como servicio independiente:

    export BI_DATABASE_URL="postgresql+psycopg2://bi_lector:...@host/erp"
    export BI_MODEL="qwen2.5-coder:7b"   # el tag que tenga descargado, exacto
    python app.py

Y queda escuchando en http://localhost:8500/api/v1/bi/query

El mismo archivo sirve como referencia de integracion: `crear_app` no hace
nada que no se pueda hacer desde una aplicacion Flask existente con
`register_blueprint(crear_blueprint(...))`.

Por que el `Engine` se crea aqui y no dentro del modulo
-------------------------------------------------------
Para que quien lo integre pueda pasar el suyo -- con su pool, su
`search_path`, su replica de lectura -- sin pelearse con una conexion que el
modulo abrio por su cuenta. El modulo consume un `Engine`; no lo impone.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from bi.api import crear_blueprint
from bi.config import AjustesBI, puerto_disponible
from bi.llm_provider import ProveedorLLM, ProveedorOllama
from bi.schema_extractor import CacheDeEsquema
from bi.security import advertencias_de_despliegue


# Donde queda la interfaz ya construida (`npm run build`), relativa a este
# archivo. Si existe, el mismo proceso sirve interfaz y API desde un solo
# puerto: una URL y un comando, que es lo que hace falta para demostrarlo.
DIST_POR_OMISION = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _carpeta_de_interfaz(ruta: str | Path | None) -> Path | None:
    """La carpeta de la interfaz construida, o None si no se construyo.

    Servir la interfaz desde el backend no es solo comodidad: al compartir
    origen, el navegador ya no hace peticiones entre dominios y CORS deja de
    hacer falta. Es la misma razon por la que en produccion nginx pone las dos
    cosas detras del mismo nombre.
    """
    candidata = Path(ruta) if ruta else Path(os.getenv("BI_FRONTEND_DIST", DIST_POR_OMISION))
    return candidata if (candidata / "index.html").is_file() else None


def crear_engine(ajustes: AjustesBI):
    """El `Engine` de solo lectura.

    `pool_pre_ping` evita el fallo clasico de un tablero: la primera consulta
    de la manana truena porque la conexion del pool lleva horas muerta del
    otro lado de un firewall.

    SQLite recibe `NullPool` porque su pool por omision no se lleva bien con
    varios hilos, y el servidor de desarrollo de Flask los usa.
    """
    if not ajustes.database_url:
        raise SystemExit(
            "Falta BI_DATABASE_URL (o DATABASE_URL).\n"
            "Ejemplos:\n"
            "  postgresql+psycopg2://bi_lector:clave@host:5432/erp\n"
            "  mysql+pymysql://bi_lector:clave@host:3306/erp\n"
            "  mssql+pyodbc://bi_lector:clave@host/erp?driver=ODBC+Driver+18+for+SQL+Server\n"
            "  sqlite:///ruta/al/archivo.db"
        )

    extra = {"poolclass": NullPool} if ajustes.database_url.startswith("sqlite") else {
        "pool_pre_ping": True, "pool_size": 5, "max_overflow": 5,
    }
    return create_engine(ajustes.database_url, future=True, **extra)


def crear_proveedor(ajustes: AjustesBI) -> ProveedorLLM:
    return ProveedorOllama(
        url=ajustes.ollama_url,
        modelo=ajustes.modelo,
        timeout=ajustes.timeout_llm,
        temperatura=ajustes.temperatura,
    )


def crear_app(
    ajustes: AjustesBI | None = None,
    *,
    engine=None,
    proveedor: ProveedorLLM | None = None,
    contexto=None,
    gancho_sql=None,
    relaciones=None,
    interfaz=None,
) -> Flask:
    ajustes = ajustes or AjustesBI.desde_entorno()
    engine = engine if engine is not None else crear_engine(ajustes)
    proveedor = proveedor if proveedor is not None else crear_proveedor(ajustes)
    dist = _carpeta_de_interfaz(interfaz)

    app = Flask(__name__, static_folder=str(dist) if dist else None,
                static_url_path="")
    app.config["JSON_SORT_KEYS"] = False

    # CORS solo si esta instalado, y solo si la interfaz NO se sirve desde
    # aqui: con el mismo origen no hay nada que abrir.
    try:
        if dist is not None:
            raise ImportError("la interfaz se sirve desde este mismo origen")

        from flask_cors import CORS

        CORS(app, resources={f"{ajustes.prefijo_api}/*": {
            "origins": list(ajustes.cors_origenes)}})
    except ImportError:
        app.logger.info("flask-cors no esta instalado; no se habilita CORS.")

    cache = CacheDeEsquema(engine, ajustes)
    app.register_blueprint(crear_blueprint(
        engine=engine,
        ajustes=ajustes,
        proveedor=proveedor,
        cache_esquema=cache,
        contexto=contexto,
        gancho_sql=gancho_sql,
        relaciones=relaciones,
    ))

    # Se dejan accesibles para las pruebas y para quien integre.
    app.extensions["bi"] = {
        "ajustes": ajustes, "engine": engine,
        "proveedor": proveedor, "cache": cache,
    }

    if dist is not None:
        @app.get("/")
        def raiz():
            return send_from_directory(dist, "index.html")

        # Cualquier ruta que no sea de la API devuelve el index: es una
        # aplicacion de una sola pagina y el enrutador vive en el navegador.
        # Las rutas de la API son literales y Werkzeug las prefiere sobre esta
        # regla con convertidor, asi que no la tapan.
        @app.get("/<path:ruta>")
        def interfaz_spa(ruta: str):
            archivo = dist / ruta
            if archivo.is_file():
                return send_from_directory(dist, ruta)
            return send_from_directory(dist, "index.html")
    else:
        @app.get("/")
        def raiz():
            return jsonify({
                "modulo": "bi-text-to-sql",
                "interfaz": "no construida -- corra `npm run build` en frontend/",
                "endpoints": [
                    f"POST {ajustes.prefijo_api}/query",
                    f"GET  {ajustes.prefijo_api}/schema",
                    f"GET  {ajustes.prefijo_api}/health",
                ],
            })

    for aviso in advertencias_de_despliegue(ajustes.database_url):
        app.logger.warning("BI: %s", aviso)

    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("BI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    ajustes = AjustesBI.desde_entorno()
    aplicacion = crear_app(ajustes)

    # 8500 y no 5001: 5001 es un puerto comun para un backend de desarrollo, y
    # en mas de una maquina de prueba ya estaba ocupado por OTRO proyecto
    # (Docker Desktop reenviando un contenedor ajeno). Cuando eso pasa, el
    # navegador termina hablando con esa otra aplicacion sin ningun aviso, y
    # se siente como si este modulo respondiera mal -- cuando ni siquiera es
    # este modulo el que contesta.
    puerto = int(os.getenv("BI_PORT", "8500"))
    host = os.getenv("BI_HOST", "127.0.0.1")

    # Se comprueba ANTES de arrancar, no despues: el servidor de desarrollo
    # de Werkzeug atrapa el OSError del bind el mismo (imprime su propio
    # aviso y llama a sys.exit(1) directo, sin volver a levantar la
    # excepcion), asi que envolver `aplicacion.run()` en un try/except aqui
    # seria codigo muerto -- confirmado probandolo contra un conflicto real.
    if not puerto_disponible(host, puerto):
        print(file=sys.stderr)
        print(f"  El puerto {puerto} ya esta ocupado por OTRO programa.", file=sys.stderr)
        print("  No es este modulo el que esta fallando -- es que algo mas ya", file=sys.stderr)
        print("  escucha ahi (a veces Docker Desktop, reenviando un contenedor", file=sys.stderr)
        print("  de otro proyecto). Use un puerto distinto:", file=sys.stderr)
        print("    BI_PORT=8501 python app.py", file=sys.stderr)
        print(file=sys.stderr)
        raise SystemExit(1)

    print(f"Modulo de BI escuchando en http://localhost:{puerto}{ajustes.prefijo_api}",
          file=sys.stderr)
    aplicacion.run(host=host, port=puerto, debug=False)
