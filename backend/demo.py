"""Demostracion: base de juguete, interfaz incluida, un solo comando.

    python demo.py        ->  http://localhost:8500

Levanta la misma aplicacion de `app.py` contra una base SQLite generica que
se siembra aqui, y sirve tambien la interfaz ya construida desde el mismo
puerto. No hace falta PostgreSQL ni una segunda terminal.

El modelo es REAL por omision, no simulado
-------------------------------------------
Si Ollama esta corriendo en esta maquina (`ollama serve`) y el modelo de
`BI_MODEL` esta descargado (`ollama pull qwen2.5-coder:7b` por omision), se
usa ese modelo real: se le puede preguntar CUALQUIER cosa sobre los datos y
la respuesta sale de una traduccion a SQL de verdad, ejecutada de verdad
contra la base. Verificado en la practica: dos preguntas libres, nunca vistas
por ningun guion, devolvieron los mismos numeros que una consulta escrita a
mano -- al centavo.

En CPU sin GPU, cada pregunta tarda con confianza entre 60 y 100 segundos de
punta a punta (medido de verdad, no estimado): la mayor parte es el modelo
generando el JSON de respuesta, token por token. Con GPU baja a segundos.

Si Ollama no esta arriba, o el modelo no esta descargado, el programa lo
detecta solo y cae a un modelo SIMULADO -- consultas fijas para un puñado de
preguntas de ejemplo, para poder enseñar el flujo (traduccion, validacion,
ejecucion, dibujo) sin esperar nada. Ante una pregunta que no cubre, lo dice;
nunca inventa una respuesta. `BI_DEMO_SCRIPTED=1` fuerza este modo aunque
haya un modelo real disponible.

La base es deliberadamente generica -- clientes, productos, empleados,
ventas -- para que se parezca a la de cualquier sistema comercial y no a la
de un cliente concreto.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app import crear_app, crear_proveedor
from bi.config import AjustesBI, puerto_disponible
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
    "ejemplo. Pruebe con una de ellas, o instale Ollama y descargue un modelo "
    "para preguntar libremente -- vea docs/DEMOSTRACION.md."
)


def _proveedor_de_guion() -> ProveedorDeGuion:
    """El modelo simulado. Es el respaldo, no el camino principal."""
    guion: dict[str, str] = {}
    for claves, respuesta in RESPUESTAS:
        texto = json.dumps(respuesta, ensure_ascii=False)
        for clave in claves:
            guion[clave] = texto
    # Sin `respuesta_fija`: ante una pregunta que no cubre, lo dice.
    return ProveedorDeGuion(guion=guion, mensaje_sin_guion=SIN_GUION)


def elegir_proveedor(ajustes: AjustesBI):
    """Real siempre que se pueda; simulado solo cuando de verdad no hay modelo.

    La demostracion tiene que preguntar cosas reales sobre datos reales -- no
    aparentarlo. Por eso el modelo real es el camino por omision: si Ollama
    esta arriba y el modelo esta descargado, se usa sin que nadie tenga que
    poner una variable de entorno para pedirlo.

    `BI_DEMO_SCRIPTED=1` fuerza el simulado aunque haya un modelo real
    disponible -- para CI, para una maquina sin GPU donde no se quiere
    esperar, o para reproducir el guion exacto de DEMOSTRACION.md.
    """
    if os.getenv("BI_DEMO_SCRIPTED") in ("1", "true", "True"):
        return _proveedor_de_guion(), False, "se pidio el modo simulado (BI_DEMO_SCRIPTED=1)"

    real = crear_proveedor(ajustes)
    if real.disponible():
        return real, True, ""

    motivo = (
        f"Ollama no responde en {ajustes.ollama_url}, o el modelo "
        f"'{ajustes.modelo}' no esta descargado (revise con `ollama list`; "
        f"el tag debe coincidir EXACTO)."
    )
    return _proveedor_de_guion(), False, motivo


def main() -> None:
    sembrar()
    ajustes = AjustesBI.desde_entorno().con(
        database_url=f"sqlite:///{RUTA}",
        limite_filas=500,
    )
    proveedor, es_real, motivo_simulado = elegir_proveedor(ajustes)
    aplicacion = crear_app(ajustes, proveedor=proveedor)

    # 8500 y no 5001: en mas de una maquina de prueba el 5001 ya estaba
    # ocupado por OTRO proyecto (Docker Desktop reenviando un contenedor
    # ajeno). Cuando eso pasa, el navegador termina hablando con esa otra
    # aplicacion sin ningun aviso, y parece que este modulo esta fallando --
    # cuando ni siquiera es este modulo el que contesta.
    puerto = int(os.getenv("BI_PORT", "8500"))
    host = os.getenv("BI_HOST", "127.0.0.1")
    hay_interfaz = aplicacion.static_folder is not None

    # Se comprueba ANTES de imprimir "lista en http://..." y antes de
    # arrancar: el servidor de desarrollo de Werkzeug atrapa el OSError del
    # bind el mismo (su propio aviso + sys.exit(1) directo, sin volver a
    # levantar la excepcion), asi que un try/except alrededor de
    # `aplicacion.run()` aqui seria codigo muerto -- confirmado probandolo
    # contra un conflicto real.
    if not puerto_disponible(host, puerto):
        print(file=sys.stderr)
        print(f"  El puerto {puerto} ya esta ocupado por OTRO programa.", file=sys.stderr)
        print("  No es esta demostracion la que esta fallando -- es que algo", file=sys.stderr)
        print("  mas ya escucha ahi (a veces Docker Desktop, reenviando un", file=sys.stderr)
        print("  contenedor de otro proyecto: revise con Docker Desktop o con", file=sys.stderr)
        print("  `netstat -ano | findstr :" + str(puerto) + "` cual programa es).", file=sys.stderr)
        print("  Use un puerto distinto:", file=sys.stderr)
        print("    set BI_PORT=8501 && python demo.py     (Windows, cmd)", file=sys.stderr)
        print("    BI_PORT=8501 python demo.py            (Linux/macOS)", file=sys.stderr)
        print(file=sys.stderr)
        raise SystemExit(1)

    print()
    print(f"  Demostracion lista en  http://localhost:{puerto}")
    if es_real:
        print(f"  Modelo: {ajustes.modelo} (real, vía Ollama en {ajustes.ollama_url})")
        print("  En CPU sin GPU una pregunta tarda con confianza entre 60 y 100")
        print("  segundos de punta a punta -- es el modelo pensando, no un error.")
    else:
        print("  Modelo: simulado (solo las preguntas de ejemplo)")
        print(f"  {motivo_simulado}")
    if not hay_interfaz:
        print("  AVISO: la interfaz no esta construida. Corra en frontend/:")
        print("         npm ci && npm run build")
    print()
    if es_real:
        print("  Pregunte lo que quiera sobre clientes, productos, empleados o")
        print("  ventas. Ejemplos: 'cuanto vendimos en total', 'ventas por mes',")
        print("  'top productos', 'ventas por ciudad', 'hazme un dashboard',")
        print("  'borra todas las ventas'  <- para ver la barrera de seguridad")
    else:
        print("  Pruebe: 'cuanto vendimos en total' · 'ventas por mes' ·")
        print("          'top productos' · 'ventas por ciudad' · 'hazme un dashboard'")
        print("          'borra todas las ventas'  <- para ver la barrera de seguridad")
    print()

    aplicacion.run(host=host, port=puerto, debug=False)


if __name__ == "__main__":
    main()
