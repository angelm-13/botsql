"""Preguntas frecuentes resueltas sin pasar por el modelo ("recetas").

Un modelo de 3B en CPU tarda 1-3 minutos y a veces inventa columnas
(`product_name`, un alias `is`...). Para las preguntas que de verdad se repiten
-- las del dataset de pruebas -- se sirve un SQL ya verificado contra el
esquema, en milisegundos y siempre igual.

No es un atajo de seguridad: la receta produce la MISMA directiva JSON que el
modelo, y esa directiva pasa por el mismo validador, el mismo filtro por rol y
el mismo ejecutor. Un rol sin permiso sobre la tabla recibe el mismo rechazo.
Lo que no coincide con ninguna receta va al modelo como siempre.

Para agregar una: un patron sobre la pregunta normalizada (minusculas, sin
acentos) y una funcion que arma la directiva. Probar el SQL en la base antes.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Callable


def _norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", (t or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[_]+", " ", s)
    s = re.sub(r"[^a-z0-9#]+$", "", re.sub(r"^[^a-z0-9#]+", "", re.sub(r"\s+", " ", s)))
    return s.strip()


def _n(m, defecto: int, tope: int = 50) -> int:
    for g in ("n", "n2", "n3"):
        try:
            v = m.group(g)
        except IndexError:
            continue
        if v:
            return max(1, min(int(v), tope))
    return defecto


def _tope(m) -> str:
    """` LIMIT n` solo si la pregunta pidio un top N; "por responsable" las trae todas."""
    return " LIMIT %d" % _n(m, 10) if any(m.groupdict().get(g) for g in ("n", "n2", "n3")) else ""


def _d(sql, titulo, tipo, x="", y="", etiqueta="", explicacion=""):
    vis = {"recommended": True, "chart_type": tipo, "title": titulo}
    if x:
        vis["x_axis"] = x
    if y:
        vis["y_axis"] = y
    vis["metric_label"] = etiqueta or y or titulo
    return {"is_dashboard": False, "sql_query": sql, "explanation": explicacion or titulo,
            "visualization": vis}


VENC = "FROM nm_incident_product n JOIN incident i ON i.id_incident = n.id_incident WHERE n.due_date < now() AND n.close_date IS NULL AND n.deletion_date IS NULL AND i.deletion_date IS NULL AND i.incident_status NOT IN ('cerrada','cancelado')"

N = r"(?:top |los |las |primeros |primeras )?(?P<n>\d{1,2})"
N2 = N.replace("<n>", "<n2>")
N3 = N.replace("<n>", "<n3>")


_ESTATUS = {
    "proyectos": ("proyect", "proyect_status", {
        "autorizados": "authorized", "entregados": "delivered", "bloqueados": "blocked",
        "borrador": "draft", "denegados": "denied", "rechazados": "denied",
        "completados": "completed", "terminados": "completed", "en proceso": "in_progress",
        "esperando material": "waiting_material", "en espera de material": "waiting_material"}),
    "tareas": ("task", "task_status", {
        "pendientes": "pendiente", "en proceso": "en_proceso", "terminadas": "terminada",
        "terminados": "terminada"}),
    "vales": ("incident", "incident_status", {
        "abiertos": "abierta", "cerrados": "cerrada", "borrador": "borrador", "en borrador": "borrador",
        "cancelados": "cancelado", "en espera": "en_espera", "en transito": "en_transito"}),
}
_ESTATUS["incidencias"] = (_ESTATUS["vales"][0], _ESTATUS["vales"][1], {
    k.replace("os", "as"): v for k, v in _ESTATUS["vales"][2].items()} | _ESTATUS["vales"][2])


class _SinReceta(Exception):
    pass


def _por_estatus(m):
    tabla, col, mapa = _ESTATUS[m.group("ent")]
    valor = mapa.get(m.group("est").strip())
    if valor is None:
        raise _SinReceta
    return _d(f"SELECT COUNT(*) AS total FROM {tabla} WHERE {col} = '{valor}' AND deletion_date IS NULL",
              f"{m.group('ent').capitalize()} {m.group('est').strip()}", "kpi_card", y="total",
              etiqueta=m.group("ent").capitalize())


RECETAS: list[tuple[re.Pattern, Callable]] = [
    (re.compile(r"^cuantos productos (hay|existen|tenemos)( registrados)?$|^total de productos$"),
     lambda m: _d("SELECT COUNT(*) AS total_productos FROM product WHERE deletion_date IS NULL",
                  "Productos registrados", "kpi_card", y="total_productos", etiqueta="Productos")),

    (re.compile(rf"^{N} productos (por|con mas|con mayores|segun) existencias?$|^top {N2} productos( por existencias?)?$"),
     lambda m: _d("SELECT descripcion AS producto, cantidad AS existencias FROM product "
                  "WHERE deletion_date IS NULL ORDER BY cantidad DESC NULLS LAST LIMIT %d" % _n(m, 8),
                  "Top %d productos por existencias" % _n(m, 8), "bar", "producto", "existencias",
                  explicacion="Productos con mayor cantidad en existencia.")),

    (re.compile(r"^(cuantas )?incidencias (hay )?por tipo$|^incidencias por tipo$"),
     lambda m: _d("SELECT t.incident_type_description AS tipo, COUNT(*) AS incidencias FROM incident n "
                  "JOIN incident_type t ON t.id_incident_type = n.id_incident_type "
                  "WHERE n.deletion_date IS NULL GROUP BY t.incident_type_description "
                  "ORDER BY incidencias DESC LIMIT 20",
                  "Incidencias por tipo", "bar", "tipo", "incidencias")),

    (re.compile(r"^(cuantas )?incidencias (hay )?por (estatus|estado)$"),
     lambda m: _d("SELECT incident_status AS estatus, COUNT(*) AS incidencias FROM incident "
                  "WHERE deletion_date IS NULL GROUP BY incident_status ORDER BY incidencias DESC",
                  "Incidencias por estatus", "bar", "estatus", "incidencias")),

    (re.compile(r"^(cuantos )?proyectos (hay )?por (estatus|estado)$"),
     lambda m: _d("SELECT proyect_status AS estatus, COUNT(*) AS total_proyectos FROM proyect "
                  "WHERE deletion_date IS NULL GROUP BY proyect_status ORDER BY total_proyectos DESC",
                  "Proyectos por estatus", "bar", "estatus", "total_proyectos")),

    (re.compile(rf"^(que )?(empleados|usuarios|responsables) (tienen|con) mas incidencias$|^(cuantas )?incidencias (hay )?por (responsable|usuario|empleado)$|^top {N} (empleados|usuarios) con mas incidencias$"),
     lambda m: _d('SELECT u.full_name AS empleado, COUNT(*) AS incidencias FROM incident n '
                  'JOIN "user" u ON u.id_user = n.id_user WHERE n.deletion_date IS NULL '
                  "GROUP BY u.full_name ORDER BY incidencias DESC" + _tope(m),
                  "Empleados con mas incidencias", "bar", "empleado", "incidencias")),

    (re.compile(rf"^(total de facturas|facturado|total facturado|monto facturado) por cliente$|^top {N} clientes por (monto facturado|facturacion|ventas)$|^{N2} clientes (con mayor facturacion|por monto facturado)$"),
     lambda m: _d("SELECT c.name AS cliente, SUM(i.total) AS total_facturado FROM invoice i "
                  "JOIN customer_supplier c ON c.id_customer_supplier = i.id_customer_supplier "
                  "WHERE i.deletion_date IS NULL GROUP BY c.name ORDER BY total_facturado DESC NULLS LAST LIMIT %d"
                  % _n(m, 10), "Total facturado por cliente", "bar", "cliente", "total_facturado")),

    (re.compile(r"^(facturas|facturacion|total facturado) por mes( en el ultimo ano)?$|^facturas emitidas por mes.*$"),
     lambda m: _d("SELECT date_trunc('month', date_emision) AS mes, SUM(total) AS total FROM invoice "
                  "WHERE deletion_date IS NULL GROUP BY 1 ORDER BY 1 LIMIT 24",
                  "Facturacion por mes", "line", "mes", "total")),

    (re.compile(r"^(cuantos|cuantas) vales (estan |hay |tienen (de )?(estatus|estado) |con (estatus|estado) |en (estatus|estado) )?(vencidos?|atrasados?)( hay| tenemos| existen| actualmente| ahorita| hoy)*$|^total de vales (vencidos|atrasados)$|^numero de vales (vencidos|atrasados)$"),
     lambda m: _d("SELECT COUNT(DISTINCT n.id_incident) AS vales_vencidos " + VENC,
                  "Vales vencidos", "kpi_card", y="vales_vencidos", etiqueta="Vales vencidos",
                  explicacion="Vales abiertos con alguna herramienta cuya fecha de devolucion ya paso.")),

    (re.compile(r"^(cuales son los |lista de |muestrame los |dame los )?vales (vencidos|atrasados)$"),
     lambda m: _d("SELECT i.id_incident AS vale, u.full_name AS responsable, MIN(n.due_date)::date AS vencio_el, "
                  "COUNT(*) AS renglones_vencidos " + VENC.replace("WHERE", "LEFT JOIN \"user\" u ON u.id_user = i.id_user WHERE", 1) +
                  " GROUP BY i.id_incident, u.full_name ORDER BY vencio_el LIMIT 50",
                  "Vales vencidos", "table", explicacion="Vales con herramientas sin devolver pasada su fecha limite.")),

    # Busqueda por codigo. El valor se limita a [A-Z0-9._-] (sin comillas ni espacios), asi que
    # entra al SQL sin riesgo de inyeccion.
    (re.compile(r"^(?:(?:que|cual) (?:producto|herramienta|articulo) (?:tiene|es|lleva) |(?:(?:buscar?|busca|muestrame|dame|info\w* (?:de|del)) )?(?:el )?(?:producto|herramienta|articulo) (?:con )?)?(?:el )?(?:codigo|clave|sku) (?P<c>[a-z0-9._-]{2,30})$"),
     lambda m: _d("SELECT product_code AS codigo, descripcion AS producto, cantidad AS existencias, product_status AS estatus "
                  "FROM product WHERE deletion_date IS NULL AND UPPER(product_code) = '%s' LIMIT 20" % m.group("c").upper(),
                  "Producto con codigo %s" % m.group("c").upper(), "table",
                  explicacion="Producto que tiene ese codigo.")),

    (re.compile(r"^(?:existencias?|cuantos hay|cuanto hay|ubicacion|donde esta(?:n)?) (?:de |del |de la |de los )?(?:producto |herramienta |articulo )?(?P<t>[a-z0-9 ]{3,40})$"),
     lambda m: _d("SELECT product_code AS codigo, descripcion AS producto, cantidad AS existencias "
                  "FROM product WHERE deletion_date IS NULL AND descripcion ILIKE '%%%s%%' "
                  "ORDER BY descripcion LIMIT 30" % re.sub(r"[^a-z0-9 ]", "", m.group("t")).strip().upper(),
                  "Existencias de %s" % m.group("t").strip(), "table",
                  explicacion="Productos cuya descripcion contiene ese texto.")),

    (re.compile(r"^(cuales son )?(las )?herramientas (mas usadas )?(en|del|de) (el )?vale (n |no |numero |#)?(?P<v>\d+)$"),
     lambda m: _d("SELECT p.descripcion AS herramienta, SUM(n.quantity) AS cantidad FROM nm_incident_product n "
                  "JOIN product p ON p.id_product = n.id_product WHERE n.id_incident = %d "
                  "AND n.deletion_date IS NULL GROUP BY p.descripcion ORDER BY cantidad DESC LIMIT 10"
                  % int(m.group("v")), "Herramientas del vale %s" % m.group("v"), "bar", "herramienta", "cantidad")),
    (re.compile(r"^(cuantos )?productos (hay )?por marca$"),
     lambda m: _d("SELECT b.brand_description AS marca, COUNT(*) AS total_productos FROM product p "
                  "JOIN brand b ON b.id_brand = p.id_marca WHERE p.deletion_date IS NULL "
                  "GROUP BY b.brand_description ORDER BY total_productos DESC",
                  "Productos por marca", "bar", "marca", "total_productos")),

    (re.compile(r"^(cual es el )?total de existencias( en (el )?inventario)?$|^cuantas existencias hay$"),
     lambda m: _d("SELECT SUM(cantidad) AS total_existencias FROM product WHERE deletion_date IS NULL",
                  "Total de existencias", "kpi_card", y="total_existencias", etiqueta="Existencias")),

    (re.compile(r"^(cual es el )?promedio de existencias( por producto)?$"),
     lambda m: _d("SELECT AVG(cantidad) AS promedio_existencias FROM product WHERE deletion_date IS NULL",
                  "Promedio de existencias por producto", "kpi_card", y="promedio_existencias",
                  etiqueta="Promedio por producto")),

    (re.compile(r"^cuantos (usuarios|personas) (son )?empleados$|^cuantos empleados hay$"),
     lambda m: _d('SELECT COUNT(*) AS total_empleados FROM "user" WHERE is_employee = true AND deletion_date IS NULL',
                  "Empleados", "kpi_card", y="total_empleados", etiqueta="Empleados")),

    (re.compile(r"^cuantas (incidencias|vales) (se )?(registraron|hay|hubo|se crearon) (este mes|en el mes)$"),
     lambda m: _d("SELECT COUNT(*) AS total_mes FROM incident WHERE deletion_date IS NULL "
                  "AND incident_date >= date_trunc('month', now())",
                  "Incidencias de este mes", "kpi_card", y="total_mes", etiqueta="Este mes")),

    # El tipo se compara contra la descripcion del catalogo, no contra el id.
    (re.compile(r"^cuantos vales (?:son |hay )?(?:de |del tipo |de tipo )(?P<t>[a-z ]{3,40})$"),
     lambda m: _d("SELECT COUNT(*) AS total FROM incident i JOIN incident_type t ON t.id_incident_type = i.id_incident_type "
                  "WHERE i.deletion_date IS NULL AND t.incident_type_description ILIKE '%%%s%%'"
                  % "%".join(w for w in re.sub(r"[^a-z ]", "", m.group("t")).split() if w not in ("de", "del", "la", "el", "por")),
                  "Vales de %s" % m.group("t").strip(), "kpi_card", y="total", etiqueta="Vales")),

    # "cuantos proyectos estan entregados": el valor guardado en la base no es la palabra
    # que se dice (`delivered`, `en_proceso`), y un modelo chico lo adivina mal.
    (re.compile(r"^(?:cuantos|cuantas) (?P<ent>proyectos|tareas|vales|incidencias) (estan |hay |se encuentran )?(?:en )?(?P<est>[a-z ]{3,25})$"),
     lambda m: _por_estatus(m)),

]


def buscar(pregunta: str) -> str | None:
    """El JSON de la directiva si la pregunta coincide con una receta, o None."""
    texto = _norm(pregunta)
    # "grafica de ...", "en barras", "en pastel": el tipo de grafica lo decide el
    # servicio; aqui solo importa QUE se pregunta.
    texto = re.sub(r"^(muestrame |dame |hazme |genera |haz )?(una |un )?(grafica|grafico|diagrama|dashboard|tablero)( de| del| con)? ", "", texto)
    texto = re.sub(r" (en|como|con) (una )?(grafica|grafico|barras|pastel|torta|dona|lineas?)( de \w+)?$", "", texto).strip()
    for patron, fabrica in RECETAS:
        m = patron.search(texto)
        if m:
            try:
                return json.dumps(fabrica(m), ensure_ascii=False)
            except _SinReceta:
                continue
    return None
