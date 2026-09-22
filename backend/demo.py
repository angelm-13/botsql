"""Demostracion: base de juguete, interfaz incluida, un solo comando.

    python demo.py        ->  http://localhost:5001

Levanta la misma aplicacion de `app.py` contra una base SQLite generica que
se siembra aqui, y sirve tambien la interfaz ya construida desde el mismo
puerto. No hace falta PostgreSQL, ni Ollama, ni una segunda terminal.

Dos modos, y la diferencia importa al enseñarlo
-----------------------------------------------
  `python demo.py`
      Modelo SIMULADO: devuelve consultas fijas para un puñado de preguntas
      de ejemplo. Sirve para enseñar el flujo completo -- traduccion,
      validacion, ejecucion, dibujo -- en cualquier maquina. Ante una
      pregunta que no cubre, lo dice; no inventa una respuesta.

  `BI_DEMO_OLLAMA=1 python demo.py`
      Modelo REAL contra la misma base. Contesta preguntas libres. Necesita
      Ollama corriendo y el modelo descargado.

La base es deliberadamente generica -- clientes, productos, empleados,
ventas -- para que se parezca a la de cualquier sistema comercial y no a la
de un cliente concreto.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app import crear_app, crear_proveedor
from bi.config import AjustesBI
from bi.llm_provider import ProveedorDeGuion

RUTA = Path(__file__).parent / "demo_bi.db"
ANIO = 2026

ESQUEMA = [
    """CREATE TABLE clientes (
        id INTEGER PRIMARY KEY,
        nombre VARCHAR(80) NOT NULL,
        ciudad VARCHAR(40),
        segmento VARCHAR(30),
        password_hash VARCHAR(120),
        api_key VARCHAR(60))""",
    """CREATE TABLE productos (
        id INTEGER PRIMARY KEY,
        nombre VARCHAR(80),
        categoria VARCHAR(40),
        precio NUMERIC(10,2))""",
    """CREATE TABLE empleados (
        id INTEGER PRIMARY KEY,
        nombre VARCHAR(80),
        puesto VARCHAR(40))""",
    """CREATE TABLE ventas (
        id INTEGER PRIMARY KEY,
        fecha DATE NOT NULL,
        id_cliente INTEGER REFERENCES clientes(id),
        id_producto INTEGER REFERENCES productos(id),
        id_empleado INTEGER REFERENCES empleados(id),
        cantidad INTEGER,
        total NUMERIC(12,2))""",
    # Las dos siguientes existen para demostrar el filtrado: no deben llegar
    # nunca al DDL que ve el modelo.
    "CREATE TABLE alembic_version (version_num VARCHAR(32))",
    "CREATE TABLE user_mfa (id INTEGER PRIMARY KEY, secret VARCHAR(40))",
]

CIUDADES = ["CDMX", "Monterrey", "Guadalajara", "Puebla", "Mérida"]
SEGMENTOS = ["Mayorista", "Minorista", "Gobierno"]
CATEGORIAS = ["Herramienta", "Insumo", "Refacción", "Servicio"]
PUESTOS = ["Vendedor", "Ejecutivo de cuenta", "Gerente regional"]
NOMBRES = ["Ana Rivas", "Luis Cordero", "Marta Peña", "Iván Soto",
           "Sofía Lara", "Hugo Márquez"]
DIAS_POR_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def sembrar() -> None:
    """Crea y llena la base de demostracion. Es determinista.

    Los importes NO son aleatorios planos: llevan una tendencia de
    crecimiento y una estacionalidad suave. Con ruido plano la grafica de
    tendencia sale como una linea horizontal con temblor, que no enseña nada
    -- y lo que se quiere mostrar es precisamente que la herramienta revela
    la forma de los datos.

    La semilla es fija para que dos personas que corran la demostracion vean
    exactamente los mismos numeros y puedan compararlos.
    """
    if RUTA.exists():
        RUTA.unlink()

    azar = random.Random(20260922)
    motor = create_engine(f"sqlite:///{RUTA}", future=True, poolclass=NullPool)

    with motor.begin() as con:
        for ddl in ESQUEMA:
            con.execute(text(ddl))

        for i in range(1, 13):
            con.execute(
                text("INSERT INTO clientes VALUES (:i,:n,:c,:s,'no-visible','no-visible')"),
                {"i": i, "n": f"Cliente {i:02d}",
                 "c": CIUDADES[i % len(CIUDADES)],
                 "s": SEGMENTOS[i % len(SEGMENTOS)]},
            )
        for i in range(1, 19):
            con.execute(
                text("INSERT INTO productos VALUES (:i,:n,:c,:p)"),
                {"i": i, "n": f"Producto {i:02d}",
                 "c": CATEGORIAS[i % len(CATEGORIAS)],
                 "p": 80 + i * 17},
            )
        for i, nombre in enumerate(NOMBRES, start=1):
            con.execute(
                text("INSERT INTO empleados VALUES (:i,:n,:p)"),
                {"i": i, "n": nombre, "p": PUESTOS[i % len(PUESTOS)]},
            )

        id_venta = 0
        for mes in range(1, 13):
            # Crecimiento del 6 % mensual y un pico hacia fin de año.
            tendencia = 1.0 + 0.06 * (mes - 1)
            estacional = 1.0 + 0.22 * math.sin((mes - 3) / 12 * 2 * math.pi)
            operaciones = max(12, round(24 * tendencia * estacional))

            for _ in range(operaciones):
                id_venta += 1
                id_producto = azar.randint(1, 18)
                precio = 80 + id_producto * 17
                cantidad = azar.randint(1, 6)
                importe = round(precio * cantidad * azar.uniform(0.9, 1.15), 2)
                con.execute(
                    text("INSERT INTO ventas VALUES (:i,:f,:c,:p,:e,:q,:t)"),
                    {"i": id_venta,
                     "f": f"{ANIO}-{mes:02d}-{azar.randint(1, DIAS_POR_MES[mes - 1]):02d}",
                     "c": azar.randint(1, 12), "p": id_producto,
                     "e": azar.randint(1, len(NOMBRES)),
                     "q": cantidad, "t": importe},
                )

    motor.dispose()


# ---------------------------------------------------------------------------
# El guion del modelo simulado
# ---------------------------------------------------------------------------
#
# Cada entrada lleva las palabras con las que la gente la pide. El orden
# IMPORTA: se toma la primera que aparece en la pregunta, asi que lo
# destructivo va primero. Si "ventas" estuviera antes, "borra todas las
# ventas" caeria en la consulta de ventas en vez de en el rechazo.

RESPUESTAS: list[tuple[tuple[str, ...], dict]] = [
    (("borra", "borrar", "elimina", "eliminar", "drop", "delete", "trunca"),
     {"error": "Acción no permitida por seguridad"}),

    (("dashboard", "tablero", "panorama", "general", "resumen"),
     {"is_dashboard": True,
      "dashboard_title": f"Panorama comercial {ANIO}",
      "widgets": [
          {"sql_query": "SELECT SUM(total) AS importe FROM ventas",
           "explanation": "Importe total vendido en el año.",
           "visualization": {"chart_type": "kpi_card", "title": "Ventas totales",
                             "metric_label": "Importe"}},
          {"sql_query": "SELECT COUNT(*) AS operaciones FROM ventas",
           "explanation": "Número de operaciones registradas.",
           "visualization": {"chart_type": "kpi_card", "title": "Operaciones",
                             "metric_label": "Ventas registradas"}},
          {"sql_query": ("SELECT substr(fecha,1,7) AS mes, SUM(total) AS importe "
                         "FROM ventas GROUP BY mes ORDER BY mes LIMIT 12"),
           "explanation": "Evolución del importe mes a mes.",
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
           "explanation": "Comparativa por categoría de producto.",
           "visualization": {"chart_type": "bar", "title": "Importe por categoría",
                             "x_axis": "categoria", "y_axis": "importe"}},
      ]}),

    (("mes", "mensual", "tendencia", "evolucion", "evolución", "temporal"),
     {"is_dashboard": False,
      "sql_query": ("SELECT substr(fecha,1,7) AS mes, SUM(total) AS importe "
                    "FROM ventas GROUP BY mes ORDER BY mes LIMIT 12"),
      "explanation": "Importe vendido por mes.",
      "visualization": {"recommended": True, "chart_type": "line",
                        "title": "Tendencia mensual", "x_axis": "mes",
                        "y_axis": "importe"}}),

    (("producto", "top", "ranking", "mas vendido", "más vendido"),
     {"is_dashboard": False,
      "sql_query": ("SELECT p.nombre AS producto, SUM(v.total) AS importe "
                    "FROM ventas v JOIN productos p ON p.id = v.id_producto "
                    "GROUP BY p.nombre ORDER BY importe DESC LIMIT 5"),
      "explanation": "Los cinco productos con mayor importe vendido.",
      "visualization": {"recommended": True, "chart_type": "bar",
                        "title": "Top 5 productos", "x_axis": "producto",
                        "y_axis": "importe"}}),

    (("ciudad", "region", "región", "plaza", "sucursal"),
     {"is_dashboard": False,
      "sql_query": ("SELECT c.ciudad AS ciudad, SUM(v.total) AS importe "
                    "FROM ventas v JOIN clientes c ON c.id = v.id_cliente "
                    "GROUP BY c.ciudad ORDER BY importe DESC"),
      "explanation": "Reparto del importe por ciudad.",
      "visualization": {"recommended": True, "chart_type": "pie",
                        "title": "Importe por ciudad", "x_axis": "ciudad",
                        "y_axis": "importe"}}),

    (("vendedor", "empleado", "quien vende", "quién vende", "equipo"),
     {"is_dashboard": False,
      "sql_query": ("SELECT e.nombre AS vendedor, SUM(v.total) AS importe "
                    "FROM ventas v JOIN empleados e ON e.id = v.id_empleado "
                    "GROUP BY e.nombre ORDER BY importe DESC"),
      "explanation": "Importe vendido por cada persona del equipo.",
      "visualization": {"recommended": True, "chart_type": "bar",
                        "title": "Ventas por vendedor", "x_axis": "vendedor",
                        "y_axis": "importe"}}),

    (("total", "vendimos", "vendido", "cuanto", "cuánto", "suma", "acumulado"),
     {"is_dashboard": False,
      "sql_query": "SELECT SUM(total) AS venta_total FROM ventas",
      "explanation": "Suma del importe de todas las ventas registradas.",
      "visualization": {"recommended": True, "chart_type": "kpi_card",
                        "title": "Ventas totales",
                        "metric_label": "Importe acumulado"}}),

    (("cliente",),
     {"is_dashboard": False,
      "sql_query": ("SELECT c.nombre AS cliente, SUM(v.total) AS importe "
                    "FROM ventas v JOIN clientes c ON c.id = v.id_cliente "
                    "GROUP BY c.nombre ORDER BY importe DESC LIMIT 10"),
      "explanation": "Los diez clientes con mayor importe comprado.",
      "visualization": {"recommended": True, "chart_type": "bar",
                        "title": "Top 10 clientes", "x_axis": "cliente",
                        "y_axis": "importe"}}),
]

# Compatibilidad: la suite usa `GUION["dashboard"]` y `GUION["total"]`.
GUION: dict[str, dict] = {claves[0]: respuesta for claves, respuesta in RESPUESTAS}

SIN_GUION = (
    "Esta demostración usa un modelo simulado, que solo cubre las preguntas de "
    "ejemplo. Pruebe con una de ellas, o arranque con BI_DEMO_OLLAMA=1 para "
    "usar el modelo real y preguntar libremente."
)


def proveedor_de_demo():
    if os.getenv("BI_DEMO_OLLAMA") in ("1", "true", "True"):
        return None       # `crear_app` usara el Ollama real

    guion: dict[str, str] = {}
    for claves, respuesta in RESPUESTAS:
        texto = json.dumps(respuesta, ensure_ascii=False)
        for clave in claves:
            guion[clave] = texto

    # Sin `respuesta_fija`: ante una pregunta que no cubre, lo dice.
    return ProveedorDeGuion(guion=guion, mensaje_sin_guion=SIN_GUION)


def main() -> None:
    sembrar()
    ajustes = AjustesBI.desde_entorno().con(
        database_url=f"sqlite:///{RUTA}",
        limite_filas=500,
    )
    proveedor = proveedor_de_demo() or crear_proveedor(ajustes)
    aplicacion = crear_app(ajustes, proveedor=proveedor)

    puerto = int(os.getenv("BI_PORT", "5001"))
    hay_interfaz = aplicacion.static_folder is not None
    real = os.getenv("BI_DEMO_OLLAMA") in ("1", "true", "True")

    print()
    print(f"  Demostracion lista en  http://localhost:{puerto}")
    print(f"  Modelo: {'Ollama real' if real else 'simulado (preguntas de ejemplo)'}")
    if not hay_interfaz:
        print("  AVISO: la interfaz no esta construida. Corra en frontend/:")
        print("         npm ci && npm run build")
    print()
    print("  Pruebe: 'cuanto vendimos en total' · 'ventas por mes' ·")
    print("          'top productos' · 'ventas por ciudad' · 'hazme un dashboard'")
    print("          'borra todas las ventas'  <- para ver la barrera de seguridad")
    print()

    aplicacion.run(host=os.getenv("BI_HOST", "127.0.0.1"), port=puerto, debug=False)


if __name__ == "__main__":
    main()
