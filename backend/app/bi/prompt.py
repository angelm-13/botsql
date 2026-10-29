"""El contrato que se le impone al modelo.

El texto es el acordado, con el esquema y el motor inyectados en tiempo de
ejecucion. Se mantiene en su propio archivo por una razon practica: el prompt
es el parametro que mas se va a tocar al afinar la precision, y no deberia
haber que abrir el codigo del servidor para cambiar una frase.

Dos anadidos al contrato base, que salieron de como fallan los modelos
pequenos en la practica y no de la teoria:

  * Se le dice la sintaxis de acotamiento del motor. Sin esto, un modelo
    entrenado mayormente con PostgreSQL escribe `LIMIT 10` contra SQL Server,
    que no lo soporta, y la consulta truena despues de haber pasado toda la
    validacion.
  * Se le da la fecha de hoy. "Ventas del mes pasado" es irresoluble sin
    ella, y el modelo -- que no tiene reloj -- se inventa un anio, casi
    siempre el de su entrenamiento.
"""

from __future__ import annotations

import re
from datetime import date

from .schema_linking import ddl_para_pregunta

EJEMPLOS_BASE = """EJEMPLOS (mismo esquema; copia el estilo, no los nombres si la pregunta es otra):
P: cuantos productos hay -> SELECT COUNT(*) AS total_productos FROM product WHERE deletion_date IS NULL
P: top 8 productos por existencias -> SELECT descripcion AS producto, cantidad AS existencias FROM product WHERE deletion_date IS NULL ORDER BY cantidad DESC LIMIT 8
P: facturado por cliente -> SELECT c.name AS cliente, SUM(i.total) AS total_facturado FROM invoice i JOIN customer_supplier c ON c.id_customer_supplier = i.id_customer_supplier WHERE i.deletion_date IS NULL GROUP BY c.name ORDER BY total_facturado DESC
P: incidencias por tipo -> SELECT t.incident_type_description AS tipo, COUNT(*) AS incidencias FROM incident n JOIN incident_type t ON t.id_incident_type = n.id_incident_type WHERE n.deletion_date IS NULL GROUP BY t.incident_type_description ORDER BY incidencias DESC
P: herramientas del vale 140 -> SELECT p.descripcion AS herramienta, SUM(n.quantity) AS cantidad FROM nm_incident_product n JOIN product p ON p.id_product = n.id_product WHERE n.id_incident = 140 AND n.deletion_date IS NULL GROUP BY p.descripcion ORDER BY cantidad DESC
P: incidencias abiertas por responsable -> SELECT u.full_name AS responsable, COUNT(*) AS abiertas FROM incident n JOIN "user" u ON u.id_user = n.id_user WHERE n.incident_status = 'abierta' AND n.deletion_date IS NULL GROUP BY u.full_name ORDER BY abiertas DESC
P: facturas por mes -> SELECT date_trunc('month', date_emision) AS mes, SUM(total) AS total FROM invoice WHERE deletion_date IS NULL GROUP BY 1 ORDER BY 1

"""

PLANTILLA = """Eres un asistente de BI experto en SQL. Conviertes preguntas en lenguaje natural en UNA consulta SQL de solo lectura y la directiva de visualizacion. Responde SOLO con JSON.

REGLAS:
1. Solo SELECT. Prohibido INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT. Si piden modificar o borrar datos responde {{"error": "Accion no permitida por seguridad"}}.
2. Usa unicamente tablas y columnas del ESQUEMA de abajo, con sus nombres exactos. No inventes campos. Cada tabla tiene su llave como id_<tabla>; las llaves foraneas se llaman id_<otra_tabla>.
3. Agrega con SUM, COUNT, AVG, GROUP BY y ordena con ORDER BY. Si una tabla trae deletion_date, filtra deletion_date IS NULL. Al ordenar DESC agrega NULLS LAST. Alias de tabla de una o dos letras que NO sean palabras reservadas (usa p, i, n, st, c; nunca is, in, on, or, to, by).
4. El sistema ya acota el resultado a {row_limit} filas: NO escribas LIMIT salvo que la pregunta pida un top N, "el mayor" o "el primero" (entonces LIMIT con ese numero exacto). Sintaxis en este motor: {limit_syntax}.
5. Hoy es {today}. Resuelve con esa fecha "este mes", "el ano pasado", "ultimos 30 dias".
6. Da un alias a cada columna calculada y usa ese mismo alias en x_axis, y_axis y metric_label.
7. Usa chart_type table por omision. Solo si el usuario pide una grafica usa bar, line, pie o area (bar para categorias, line para fechas). Un conteo o total unico usa kpi_card.

FORMATO (JSON estricto, sin markdown):
Una grafica o KPI:
{{"is_dashboard": false, "sql_query": "SELECT ...", "explanation": "que calcula, en una frase", "visualization": {{"recommended": true, "chart_type": "bar | line | pie | kpi_card | table", "title": "titulo", "x_axis": "columna_x", "y_axis": "columna_y", "metric_label": "etiqueta si es kpi_card"}}}}

Si piden un "Dashboard" o analisis general:
{{"is_dashboard": true, "dashboard_title": "titulo", "widgets": [{{"sql_query": "...", "explanation": "...", "visualization": {{"chart_type": "kpi_card", "title": "...", "metric_label": "..."}}}}, {{"sql_query": "...", "explanation": "...", "visualization": {{"chart_type": "bar", "title": "...", "x_axis": "...", "y_axis": "..."}}}}]}}

GLOSARIO DEL NEGOCIO (usa estas tablas y valores, son los reales):
- vale = incidencia: tabla incident (id_incident, incident_date, incident_status, id_user, id_incident_type). incident_status vale: abierta, borrador, cancelado, cerrada, en_espera, en_transito. Tipo en incident_type.incident_type_description (Prestamo Material, Jornada, Comida, Reparacion, Destruccion, Dañado, Extraviado...).
- vale VENCIDO / atrasado (NO existe estatus 'vencido'): vale abierto con renglones en nm_incident_product con due_date < now() y close_date IS NULL (herramienta sin devolver), con incident_status NOT IN ('cerrada','cancelado').
- herramientas/articulos/productos de un vale: nm_incident_product (id_incident, id_product, quantity, direction entrada|salida) unida a product.
- producto/herramienta = product (descripcion, cantidad, product_code, product_status: ENTRADA, SALIDA, DAÑADO, EXTRAVIADO...). Existencias por ubicacion: inventory_stock (id_product, id_location, quantity) con location.location_description.
- cliente/proveedor = customer_supplier (name). factura = invoice (date_emision, total, invoice_status, id_customer_supplier).
- existencias de un producto = product.cantidad; "total de existencias" = SUM(product.cantidad). product.id_marca -> brand(brand_description), product.id_familia -> product_family(product_family_description). inventory_stock es solo por ubicacion.
- rol de un usuario = permission.permission_description, unido por "user".id_permission = permission.id_permission (NO uses user_type). usuarios por rol = COUNT(*) agrupado por permission_description.
- empleado = "user" con is_employee = true. Estatus de proyecto en espanol: borrador=draft, autorizado=authorized, en proceso=in_progress, esperando material=waiting_material, bloqueado=blocked, completado=completed, entregado=delivered, rechazado=denied.
- proyecto/orden de trabajo = proyect (title, proyect_status: draft, authorized, in_progress, waiting_material, blocked, completed, delivered, denied; total_cost). tarea = task (id_proyect, task_status, title).
- empleado/usuario/responsable = "user" (first_name, last_name_father, full_name). Escribe SIEMPRE "user" entre comillas dobles: sin comillas es una palabra reservada.

{ejemplos}### MOTOR: {db_engine_name}

### ESQUEMA:
{dynamic_db_schema}

### PREGUNTA DEL USUARIO:
{user_query}"""


_TOP_N = re.compile(
    r"\b(?:top|los|las|primeros|primeras|mejores|principales|mayores|menores)\s+(\d{1,3})\b"
    r"|\b(\d{1,3})\s+(?:mejores|principales|primeros|primeras|mayores|menores|productos|clientes|"
    r"proveedores|registros|elementos)\b",
    re.IGNORECASE,
)


def detectar_top_n(pregunta: str) -> int | None:
    """El N de un "top N" / "los 8 mejores", si la pregunta lo pide.

    El modelo chico copiaba el numero del ejemplo del prompt ("Top 5") en vez
    del que pidio el usuario; por eso el numero se lee aqui y se le dice al
    modelo de forma explicita.
    """
    m = _TOP_N.search(pregunta or "")
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    return n if 1 <= n <= 100 else None


def construir_prompt(
    pregunta: str,
    esquema,
    *,
    limite_filas: int,
    hoy: date | None = None,
    max_widgets: int = 8,
    ejemplos: str = "",
) -> str:
    """Arma el prompt final para una pregunta concreta.

    `esquema` es un `EsquemaDB`; se pide el objeto y no el texto para que el
    motor y la sintaxis de acotamiento salgan de la misma fuente que el DDL y
    no puedan quedar desalineados.
    """
    texto = PLANTILLA.format(
        db_engine_name=esquema.motor_legible,
        dynamic_db_schema=ddl_para_pregunta(esquema, pregunta),
        limit_syntax=esquema.sintaxis_de_limite,
        row_limit=limite_filas,
        today=(hoy or date.today()).isoformat(),
        user_query=pregunta,
        ejemplos=ejemplos or EJEMPLOS_BASE,
    )
    texto += f"\n\n(Un dashboard no puede tener mas de {max_widgets} widgets.)"
    n = detectar_top_n(pregunta)
    if n:
        texto += (f"\n(El usuario pidio EXACTAMENTE {n} resultados: usa ORDER BY y "
                  f"LIMIT {n}; ni mas ni menos.)")
    return texto
