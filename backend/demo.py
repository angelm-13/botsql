"""Servidor de demostracion: base de juguete y modelo simulado.

Sirve para ver el modulo funcionando de punta a punta sin PostgreSQL, sin
Ollama y sin GPU:

    python demo.py

Levanta en http://localhost:5001 la misma aplicacion de `app.py`, pero contra
una base SQLite sembrada aqui y con `ProveedorDeGuion` en lugar del modelo. El
guion responde a cuatro preguntas de ejemplo, incluida una que el "modelo"
rechaza por seguridad, para poder probar ese camino tambien.

Con `BI_DEMO_OLLAMA=1` usa el Ollama real contra la misma base de juguete: es
la forma mas barata de comprobar si un modelo concreto respeta el contrato,
antes de apuntarlo a la base de un cliente.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app import crear_app, crear_proveedor
from bi.config import AjustesBI
from bi.llm_provider import ProveedorDeGuion

RUTA = Path(__file__).parent / "demo_bi.db"

ESQUEMA = [
    """CREATE TABLE clientes (
        id INTEGER PRIMARY KEY,
        nombre VARCHAR(80) NOT NULL,
        ciudad VARCHAR(40),
        password_hash VARCHAR(120),
        api_key VARCHAR(60))""",
    """CREATE TABLE productos (
        id INTEGER PRIMARY KEY,
        nombre VARCHAR(80),
        categoria VARCHAR(40),
        precio NUMERIC(10,2))""",
    """CREATE TABLE ventas (
        id INTEGER PRIMARY KEY,
        fecha DATE NOT NULL,
        id_cliente INTEGER REFERENCES clientes(id),
        id_producto INTEGER REFERENCES productos(id),
        cantidad INTEGER,
        total NUMERIC(12,2))""",
    # Las dos siguientes existen para demostrar el filtrado: no deben llegar
    # nunca al DDL que ve el modelo.
    "CREATE TABLE alembic_version (version_num VARCHAR(32))",
    "CREATE TABLE user_mfa (id INTEGER PRIMARY KEY, secret VARCHAR(40))",
]

CIUDADES = ["CDMX", "Monterrey", "Guadalajara", "Puebla", "Mérida"]
CATEGORIAS = ["Herramienta", "Insumo", "Refacción", "Servicio"]


def sembrar() -> None:
    if RUTA.exists():
        RUTA.unlink()

    motor = create_engine(f"sqlite:///{RUTA}", future=True, poolclass=NullPool)
    with motor.begin() as con:
        for ddl in ESQUEMA:
            con.execute(text(ddl))

        for i in range(1, 13):
            con.execute(
                text("INSERT INTO clientes VALUES (:i,:n,:c,'no-visible','no-visible')"),
                {"i": i, "n": f"Cliente {i:02d}", "c": CIUDADES[i % len(CIUDADES)]},
            )
        for i in range(1, 19):
            con.execute(
                text("INSERT INTO productos VALUES (:i,:n,:c,:p)"),
                {"i": i, "n": f"Producto {i:02d}",
                 "c": CATEGORIAS[i % len(CATEGORIAS)], "p": 80 + i * 17},
            )
        for i in range(1, 361):
            mes = (i % 12) + 1
            con.execute(
                text("INSERT INTO ventas VALUES (:i,:f,:c,:p,:q,:t)"),
                {"i": i, "f": f"2026-{mes:02d}-{(i % 27) + 1:02d}",
                 "c": (i % 12) + 1, "p": (i % 18) + 1,
                 "q": (i % 5) + 1, "t": round(320.5 + (i % 37) * 41.3, 2)},
            )
    motor.dispose()


GUION = {
    "total": {
        "is_dashboard": False,
        "sql_query": "SELECT SUM(total) AS venta_total FROM ventas",
        "explanation": "Suma el importe de todas las ventas registradas.",
        "visualization": {"recommended": True, "chart_type": "kpi_card",
                          "title": "Ventas totales", "metric_label": "Importe acumulado"},
    },
    "mes": {
        "is_dashboard": False,
        "sql_query": ("SELECT substr(fecha,1,7) AS mes, SUM(total) AS importe "
                      "FROM ventas GROUP BY mes ORDER BY mes LIMIT 12"),
        "explanation": "Importe vendido por mes.",
        "visualization": {"recommended": True, "chart_type": "line",
                          "title": "Tendencia mensual", "x_axis": "mes", "y_axis": "importe"},
    },
    "producto": {
        "is_dashboard": False,
        "sql_query": ("SELECT p.nombre AS producto, SUM(v.total) AS importe "
                      "FROM ventas v JOIN productos p ON p.id = v.id_producto "
                      "GROUP BY p.nombre ORDER BY importe DESC LIMIT 5"),
        "explanation": "Los cinco productos con mayor importe vendido.",
        "visualization": {"recommended": True, "chart_type": "bar",
                          "title": "Top 5 productos", "x_axis": "producto", "y_axis": "importe"},
    },
    "dashboard": {
        "is_dashboard": True,
        "dashboard_title": "Panorama comercial 2026",
        "widgets": [
            {"sql_query": "SELECT SUM(total) AS importe FROM ventas",
             "explanation": "Importe total vendido.",
             "visualization": {"chart_type": "kpi_card", "title": "Ventas totales",
                               "metric_label": "Importe"}},
            {"sql_query": "SELECT COUNT(*) AS operaciones FROM ventas",
             "explanation": "Numero de operaciones.",
             "visualization": {"chart_type": "kpi_card", "title": "Operaciones",
                               "metric_label": "Ventas registradas"}},
            {"sql_query": ("SELECT substr(fecha,1,7) AS mes, SUM(total) AS importe "
                           "FROM ventas GROUP BY mes ORDER BY mes LIMIT 12"),
             "explanation": "Evolucion mes a mes.",
             "visualization": {"chart_type": "line", "title": "Tendencia mensual",
                               "x_axis": "mes", "y_axis": "importe"}},
            {"sql_query": ("SELECT c.ciudad AS ciudad, SUM(v.total) AS importe "
                           "FROM ventas v JOIN clientes c ON c.id = v.id_cliente "
                           "GROUP BY c.ciudad ORDER BY importe DESC"),
             "explanation": "Reparto del importe por ciudad.",
             "visualization": {"chart_type": "pie", "title": "Importe por ciudad",
                               "x_axis": "ciudad", "y_axis": "importe"}},
            {"sql_query": ("SELECT p.categoria AS categoria, SUM(v.total) AS importe "
                           "FROM ventas v JOIN productos p ON p.id = v.id_producto "
                           "GROUP BY p.categoria ORDER BY importe DESC"),
             "explanation": "Comparativa por categoria de producto.",
             "visualization": {"chart_type": "bar", "title": "Importe por categoría",
                               "x_axis": "categoria", "y_axis": "importe"}},
        ],
    },
    # El camino del rechazo: el contrato dice que ante una peticion destructiva
    # el modelo debe contestar con un error, y el backend lo convierte en 403.
    "borra": {"error": "Acción no permitida por seguridad"},
}


def proveedor_de_demo():
    if os.getenv("BI_DEMO_OLLAMA") in ("1", "true", "True"):
        return None       # `crear_app` usara el Ollama real
    return ProveedorDeGuion(
        guion={clave: json.dumps(valor, ensure_ascii=False) for clave, valor in GUION.items()},
        respuesta_fija=json.dumps(GUION["total"], ensure_ascii=False),
    )


def main() -> None:
    sembrar()
    ajustes = AjustesBI.desde_entorno().con(
        database_url=f"sqlite:///{RUTA}",
        limite_filas=500,
    )
    proveedor = proveedor_de_demo() or crear_proveedor(ajustes)
    aplicacion = crear_app(ajustes, proveedor=proveedor)

    print(f"Demo en http://localhost:5001{ajustes.prefijo_api}  (base: {RUTA.name})")
    print("Pruebe: 'ventas totales', 'ventas por mes', 'top productos',")
    print("        'hazme un dashboard', 'borra todas las ventas'")
    aplicacion.run(host="127.0.0.1", port=int(os.getenv("BI_PORT", "5001")), debug=False)


if __name__ == "__main__":
    main()
