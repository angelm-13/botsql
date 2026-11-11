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
        "esperando material": "waiting_material", "en espera de material": "waiting_material",
        "recolectados": "collected"}),
    "tareas": ("task", "task_status", {
        "pendientes": "pendiente", "en proceso": "en_proceso", "terminadas": "terminada",
        "terminados": "terminada"}),
    "vales": ("incident", "incident_status", {
        "abiertos": "abierta", "cerrados": "cerrada", "borrador": "borrador", "en borrador": "borrador",
        "cancelados": "cancelado", "en espera": "en_espera", "en transito": "en_transito"}),
}
_ESTATUS["incidencias"] = (_ESTATUS["vales"][0], _ESTATUS["vales"][1], {
    k.replace("os", "as"): v for k, v in _ESTATUS["vales"][2].items()} | _ESTATUS["vales"][2])
# Solo los estatus que existen en los datos reales; el resto sigue al modelo (`_SinReceta`).
_ESTATUS["ordenes de compra"] = ("purchase_order", "order_status", {
    "autorizadas": "authorized", "pendientes de autorizacion": "pending_authorization",
    "por autorizar": "pending_authorization"})


def _tablero(titulo, *partes):
    """Un dashboard hecho de varias directivas de `_d`: es lo mas lento de pedirle al modelo
    (un JSON largo con varias consultas) y lo primero que se enseña, asi que va resuelto."""
    return {"is_dashboard": True, "dashboard_title": titulo,
            "widgets": [{k: p[k] for k in ("sql_query", "explanation", "visualization")} for p in partes]}


class _SinReceta(Exception):
    pass


def _por_estatus(m):
    tabla, col, mapa = _ESTATUS[m.group("ent")]
    est = m.group("est").strip()
    # "en proceso" / "proceso", "en borrador" / "borrador": el "en" no cambia el estatus.
    # Tambien singular ("denegado" -> "denegados"): el mapa se escribio en plural.
    valor = next((mapa[k] for k in (est, re.sub(r"^en ", "", est), "en " + est, est + "s", est + "es") if k in mapa), None)
    if valor is None:
        raise _SinReceta
    return _d(f"SELECT COUNT(*) AS total FROM {tabla} WHERE {col} = '{valor}' AND deletion_date IS NULL",
              f"{m.group('ent').capitalize()} {m.group('est').strip()}", "kpi_card", y="total",
              etiqueta=m.group("ent").capitalize())


# Totales y desgloses que no dependen de interpretar nada: nombre que se dice -> (tabla, columna de
# estatus o None). "vales" e "incidencias" son la misma tabla.
_CONTABLES = {
    "productos": ("product", "product_status"), "articulos": ("product", None), "materiales": ("material", None),
    "vales": ("incident", "incident_status"), "incidencias": ("incident", "incident_status"),
    "proyectos": ("proyect", "proyect_status"), "tareas": ("task", "task_status"),
    "facturas": ("invoice", "invoice_status"), "usuarios": ('"user"', None),
    # Salen de las preguntas reales de la bitacora (bi_query_log) que fallaban o iban al modelo.
    "ordenes de compra": ("purchase_order", "order_status"), "documentos": ("document", "status"),
    "familias de producto": ("product_family", None), "familias": ("product_family", None),
    "marcas de herramientas": ("brand", None), "marcas": ("brand", None), "departamentos": ("department", None),
    "clientes y proveedores": ("customer_supplier", None),
    "renglones de vale": ("nm_incident_product", None), "renglones de vales": ("nm_incident_product", None),
    "tipos de vale": ("incident_type", None), "tipos de incidencia": ("incident_type", None),
}
# Las frases largas primero ("familias de producto" antes que "familias"): la alternancia toma la primera que cabe.
_CONT = "|".join(sorted(_CONTABLES, key=len, reverse=True))
_CONT_ESTATUS = "|".join(sorted((e for e, (_, c) in _CONTABLES.items() if c), key=len, reverse=True))
_COLA = r"(?: hay| tenemos| existen| actualmente| ahorita| hoy)*"


def _alias(ent):
    return re.sub(r"\W+", "_", ent)


def _total(ent):
    return _d(f"SELECT COUNT(*) AS total_{_alias(ent)} FROM {_CONTABLES[ent][0]} WHERE deletion_date IS NULL",
              f"{ent.capitalize()} registrados", "kpi_card", y=f"total_{_alias(ent)}", etiqueta=ent.capitalize())


def _por_columna(ent):
    tabla, col = _CONTABLES[ent]
    return _d(f"SELECT {col} AS estatus, COUNT(*) AS total_{_alias(ent)} FROM {tabla} "
              f"WHERE deletion_date IS NULL GROUP BY {col} ORDER BY total_{_alias(ent)} DESC",
              f"{ent.capitalize()} por estatus", "bar", "estatus", f"total_{_alias(ent)}")


# Existencias: la regla de "agotado" es cantidad = 0 (la misma consulta de oro del conjunto de validacion).
_EXIST = "FROM product WHERE deletion_date IS NULL"

# Estatus de producto: se guarda en mayusculas y, a veces, con n con tilde (valores reales de la base).
_ESTATUS_PRODUCTO = {"extraviados": "EXTRAVIADO", "danados": "DAÑADO", "destruidos": "DESTRUCCION",
                     "en entrada": "ENTRADA", "entrada": "ENTRADA", "en salida": "SALIDA", "salida": "SALIDA"}

# Periodos de "se crearon este ...": lo que se dice -> argumento de date_trunc.
_PERIODO = {"este mes": "month", "en el mes": "month", "este anio": "year", "este ano": "year", "en el anio": "year",
            "en el ano": "year", "esta semana": "week", "hoy": "day"}

# Lo que el usuario llama material/marca/familia/ubicacion de un producto -> (tabla, columna de product,
# llave de la tabla, columna con el nombre). En product la marca es `id_marca` y la familia `id_familia`
# (en material son id_brand e id_product_family): por eso el modelo las confundia.
_DIMENSIONES = {
    "material": ("material", "id_material", "id_material", "material_description"),
    "marca": ("brand", "id_marca", "id_brand", "brand_description"),
    "familia": ("product_family", "id_familia", "id_product_family", "product_family_description"),
    "ubicacion": ("location", "id_location", "id_location", "location_description"),
}
_DIM_FRASE = (r"^{inicio} (?:como |con |de |del |de la |en la |en el |en )?(?:el |la )?(?:id )?"
              r"(?P<dim>" + "|".join(_DIMENSIONES) + r") [\"'“”]?(?P<v>[a-z0-9][a-z0-9 ]{{1,38}}?)[\"'“”]?$")


def _comodin(valor):
    """'desarmador de cruz' -> 'DESARMADOR%CRUZ' para un ILIKE; solo [a-z0-9 ], asi que no hay inyeccion."""
    palabras = [w for w in re.sub(r"[^a-z0-9 ]", "", valor).split() if w not in ("de", "del", "la", "el", "por")]
    if not palabras:
        raise _SinReceta
    return "%".join(palabras).upper()


def _productos_por_dimension(m, contar):
    tabla, fk, pk, nombre = _DIMENSIONES[m.group("dim")]
    patron = _comodin(m.group("v"))
    union = f"FROM product p JOIN {tabla} t ON t.{pk} = p.{fk} WHERE p.deletion_date IS NULL AND t.{nombre} ILIKE '%{patron}%'"
    titulo = f"Productos con {m.group('dim')} {m.group('v').strip()}"
    if contar:
        return _d(f"SELECT COUNT(*) AS total_productos {union}", titulo, "kpi_card", y="total_productos",
                  etiqueta="Productos", explicacion=f"Productos cuyo {m.group('dim')} (campo {fk}) contiene ese texto.")
    return _d(f"SELECT p.product_code AS codigo, p.descripcion AS producto, p.cantidad AS existencias, t.{nombre} AS {m.group('dim')} {union} ORDER BY p.descripcion",
              titulo, "table", explicacion=f"Productos cuyo {m.group('dim')} (campo {fk}) contiene ese texto.")


RECETAS: list[tuple[re.Pattern, Callable]] = [
    # "dashboard general de operaciones": `buscar` ya le quita el "dashboard" del principio.
    (re.compile(r"^(general|operaciones)( de (las )?operaciones)?$|^(resumen|panorama)( general)?( de (las )?operaciones)?$"),
     lambda m: _tablero(
         "Panorama general de operaciones",
         _d("SELECT COUNT(*) AS total_productos FROM product WHERE deletion_date IS NULL",
            "Productos registrados", "kpi_card", y="total_productos", etiqueta="Productos"),
         _d("SELECT COUNT(*) AS total FROM incident WHERE incident_status = 'abierta' AND deletion_date IS NULL",
            "Vales abiertos", "kpi_card", y="total", etiqueta="Vales abiertos"),
         _d("SELECT COUNT(DISTINCT n.id_incident) AS vales_vencidos " + VENC,
            "Vales vencidos", "kpi_card", y="vales_vencidos", etiqueta="Vales vencidos",
            explicacion="Vales abiertos con alguna herramienta cuya fecha de devolucion ya paso."),
         _d("SELECT t.incident_type_description AS tipo, COUNT(*) AS incidencias FROM incident n "
            "JOIN incident_type t ON t.id_incident_type = n.id_incident_type "
            "WHERE n.deletion_date IS NULL GROUP BY t.incident_type_description "
            "ORDER BY incidencias DESC LIMIT 20",
            "Incidencias por tipo", "bar", "tipo", "incidencias"),
         _d("SELECT descripcion AS producto, cantidad AS existencias FROM product "
            "WHERE deletion_date IS NULL ORDER BY cantidad DESC NULLS LAST LIMIT 8",
            "Top 8 productos por existencias", "bar", "producto", "existencias"),
         _d("SELECT date_trunc('month', date_emision) AS mes, SUM(total) AS total FROM invoice "
            "WHERE deletion_date IS NULL GROUP BY 1 ORDER BY 1 LIMIT 24",
            "Facturacion por mes", "line", "mes", "total"))),

    (re.compile(r"^cuantos productos (hay|existen|tenemos)( registrados)?$|^total de productos$"),
     lambda m: _d("SELECT COUNT(*) AS total_productos FROM product WHERE deletion_date IS NULL",
                  "Productos registrados", "kpi_card", y="total_productos", etiqueta="Productos")),

    (re.compile(rf"^{N} productos (por|con mas|con mayores|segun) existencias?$|^top {N2} productos( por existencias?)?$"),
     lambda m: _d("SELECT descripcion AS producto, cantidad AS existencias FROM product "
                  "WHERE deletion_date IS NULL ORDER BY cantidad DESC NULLS LAST LIMIT %d" % _n(m, 8),
                  "Top %d productos por existencias" % _n(m, 8), "bar", "producto", "existencias",
                  explicacion="Productos con mayor cantidad en existencia.")),

    (re.compile(r"^(cuantas |cuantos )?(?:incidencias|vales) (hay )?(?:por|de cada) tipo$"),
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

    (re.compile(rf"^(que )?(empleados|usuarios|responsables) (tienen|con) mas incidencias$|^(cuantas |cuantos )?(?:incidencias|vales) (hay )?por (responsable|usuario|empleado)$|^top {N} (empleados|usuarios) con mas incidencias$"),
     lambda m: _d('SELECT u.full_name AS empleado, COUNT(*) AS incidencias FROM incident n '
                  'JOIN "user" u ON u.id_user = n.id_user WHERE n.deletion_date IS NULL '
                  "GROUP BY u.full_name ORDER BY incidencias DESC" + _tope(m),
                  "Empleados con mas incidencias", "bar", "empleado", "incidencias")),

    (re.compile(rf"^(total de facturas|facturado|total facturado|monto facturado) por cliente$|^top {N} clientes por (monto facturado|facturacion|ventas)$|^{N2} clientes (con mayor facturacion|por monto facturado)$"),
     lambda m: _d("SELECT c.name AS cliente, SUM(i.total) AS total_facturado FROM invoice i "
                  "JOIN customer_supplier c ON c.id_customer_supplier = i.id_customer_supplier "
                  "WHERE i.deletion_date IS NULL GROUP BY c.name ORDER BY total_facturado DESC NULLS LAST LIMIT %d"
                  % _n(m, 10), "Total facturado por cliente", "bar", "cliente", "total_facturado")),

    (re.compile(r"^(facturas|facturacion|total facturado) por mes( en el ultimo ano)?$|^facturas emitidas por mes.*$|^cuanto se ha facturado por mes$"),
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

    # "existencias por ubicacion" es un desglose, no el nombre de un producto: se resuelve aqui, antes que la de abajo.
    (re.compile(r"^(?:cuantas )?existencias por ubicacion$|^(?:cuanto|que) (?:hay|existencias hay) por ubicacion$"),
     lambda m: _d("SELECT COALESCE(l.location_description, '(sin ubicacion)') AS ubicacion, SUM(s.quantity) AS existencias "
                  "FROM inventory_stock s LEFT JOIN location l ON l.id_location = s.id_location "
                  "GROUP BY l.location_description ORDER BY existencias DESC",
                  "Existencias por ubicacion", "bar", "ubicacion", "existencias",
                  explicacion="Suma del saldo por sitio (inventory_stock); el saldo se lleva por ubicacion.")),

    (re.compile(r"^(?:existencias?|cuantos hay|cuanto hay|ubicacion|donde esta(?:n)?) (?:de |del |de la |de los )?(?:producto |herramienta |articulo )?(?!por )(?P<t>[a-z0-9 ]{3,40})$"),
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
    (re.compile(r"^(cuantos )?productos (hay )?por marca$|^marcas con mas productos$"),
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

    (re.compile(r"^(cuantos )?usuarios (hay )?por (rol|perfil|permiso)$"),
     lambda m: _d('SELECT p.permission_description AS rol, COUNT(*) AS usuarios FROM "user" u '
                  "JOIN permission p ON p.id_permission = u.id_permission WHERE u.deletion_date IS NULL "
                  "GROUP BY p.permission_description ORDER BY usuarios DESC",
                  "Usuarios por rol", "bar", "rol", "usuarios")),

    (re.compile(r"^cuantos (usuarios|personas) (son )?empleados$|^cuantos empleados (hay|tenemos|existen|tiene la empresa)$"),
     lambda m: _d('SELECT COUNT(*) AS total_empleados FROM "user" WHERE is_employee = true AND deletion_date IS NULL',
                  "Empleados", "kpi_card", y="total_empleados", etiqueta="Empleados")),

    (re.compile(r"^cuantas (incidencias|vales) (se )?(registraron|hay|hubo|se crearon) (este mes|en el mes)$"),
     lambda m: _d("SELECT COUNT(*) AS total_mes FROM incident WHERE deletion_date IS NULL "
                  "AND incident_date >= date_trunc('month', now())",
                  "Incidencias de este mes", "kpi_card", y="total_mes", etiqueta="Este mes")),

    # El tipo se compara contra la descripcion del catalogo, no contra el id.
    (re.compile(r"^cuantos vales (?:son |hay )?(?:de |del tipo |de tipo )(?P<t>(?!(?:cada|por|todos|todas)\b)[a-z ]{3,40})$"),
     lambda m: _d("SELECT COUNT(*) AS total FROM incident i JOIN incident_type t ON t.id_incident_type = i.id_incident_type "
                  "WHERE i.deletion_date IS NULL AND t.incident_type_description ILIKE '%%%s%%'"
                  % "%".join(w for w in re.sub(r"[^a-z ]", "", m.group("t")).split() if w not in ("de", "del", "la", "el", "por")),
                  "Vales de %s" % m.group("t").strip(), "kpi_card", y="total", etiqueta="Vales")),

    # "cuantos proyectos estan entregados": el valor guardado en la base no es la palabra
    # que se dice (`delivered`, `en_proceso`), y un modelo chico lo adivina mal.
    (re.compile(r"^(?:cuantos|cuantas) (?P<ent>proyectos|tareas|vales|incidencias) (estan |hay |se encuentran )?(?:en )?(?P<est>[a-z ]{3,25})$"),
     lambda m: _por_estatus(m)),

    # --- Ampliacion: formas naturales de preguntar lo mismo. Todas al final: las anteriores ganan.
    (re.compile(rf"^(?:cuantos|cuantas) (?P<ent>{_CONT}) (?:hay|existen|tenemos|tiene el sistema)(?: registrad[oa]s)?(?: en total| en el sistema)?$"
                rf"|^(?:total|numero) de (?P<ent2>{_CONT})(?: registrad[oa]s)?$"),
     lambda m: _total(m.group("ent") or m.group("ent2"))),

    (re.compile(rf"^(?:cuantos |cuantas )?(?P<ent>{_CONT_ESTATUS}) (?:hay )?por (?:estatus|estado)$"),
     lambda m: _por_columna(m.group("ent"))),

    # "vales abiertos", "cuantos vales abiertos hay", "tareas pendientes": un estatus desconocido
    # sigue al modelo (`_SinReceta`).
    (re.compile(rf"^(?:cuantos |cuantas )?(?P<ent>proyectos|tareas|vales|incidencias|ordenes de compra) (?:estan |se encuentran |se tienen |tienen |son )?"
                rf"(?:de estado |en estado |con estado |como )?(?P<est>[a-z ]{{3,27}}?){_COLA}$"),
     lambda m: _por_estatus(m)),

    (re.compile(r"^cuantos productos (?:estan |hay |tenemos )?(?:agotados|sin existencias?|sin stock|con existencias? en cero|con cero existencias?)" + _COLA + r"$"
                r"|^cuantos productos tienen (?:existencias? |stock )?(?:en )?cero$"),
     lambda m: _d(f"SELECT COUNT(*) AS total_agotados {_EXIST} AND cantidad = 0",
                  "Productos agotados", "kpi_card", y="total_agotados", etiqueta="Agotados",
                  explicacion="Productos con existencia en cero.")),

    (re.compile(r"^(?:cuales son los |dame los |muestrame los |lista de )?productos (?:agotados|sin existencias?|sin stock|con existencias? en cero)$"),
     lambda m: _d(f"SELECT product_code AS codigo, descripcion AS producto, cantidad AS existencias {_EXIST} "
                  "AND cantidad = 0 ORDER BY descripcion",
                  "Productos agotados", "table", explicacion="Productos con existencia en cero.")),

    (re.compile(r"^(?:cual es el |que )?producto con (?P<mm>mas|mayor|menos|menor) existencias?$"),
     lambda m: _d(f"SELECT descripcion AS producto, cantidad AS existencias {_EXIST} ORDER BY cantidad "
                  + ("DESC" if m.group("mm") in ("mas", "mayor") else "ASC") + " NULLS LAST LIMIT 1",
                  "Producto con %s existencias" % ("mas" if m.group("mm") in ("mas", "mayor") else "menos"), "table")),

    (re.compile(r"^(?:top )?(?:los |las )?(?P<n>\d{1,2}) productos con (?:menos|menor) existencias?$|^productos con menos existencias?$"),
     lambda m: _d(f"SELECT descripcion AS producto, cantidad AS existencias {_EXIST} ORDER BY cantidad ASC NULLS LAST LIMIT %d"
                  % _n(m, 10), "Top %d productos con menos existencias" % _n(m, 10), "bar", "producto", "existencias")),

    # Renglones de vales aun sin devolver (consulta de oro v12).
    (re.compile(r"^cuantas herramientas (?:estan )?pendientes de devolver" + _COLA + r"$"),
     lambda m: _d("SELECT COUNT(*) AS pendientes FROM nm_incident_product WHERE deletion_date IS NULL AND close_date IS NULL",
                  "Herramientas pendientes de devolver", "kpi_card", y="pendientes", etiqueta="Pendientes",
                  explicacion="Renglones de vales que aun no se devuelven.")),

    # "cuantos productos tienen como ID Material 'desarmador'": el nombre vive en la tabla del catalogo
    # (JOIN) y esta en mayusculas y mas largo que lo que se dice, asi que se compara con ILIKE, no con =.
    # El valor se limita a [a-z0-9 ] (sin comillas), asi que entra al SQL sin riesgo de inyeccion.
    (re.compile(_DIM_FRASE.format(inicio=r"cuantos productos (?:tienen|son|hay|estan)")),
     lambda m: _productos_por_dimension(m, contar=True)),

    (re.compile(_DIM_FRASE.format(inicio=r"(?:que |cuales )?productos (?:tienen|son|hay|estan)")),
     lambda m: _productos_por_dimension(m, contar=False)),

    # --- Segunda ronda: preguntas reales de la bitacora que fallaban (JSON invalido) o tardaban minutos.
    (re.compile(r"^cuantos productos (?:estan |hay )?(?P<est>extraviados|danados|destruidos|en entrada|entrada|en salida|salida)" + _COLA + r"$"),
     lambda m: _d(f"SELECT COUNT(*) AS total_productos {_EXIST} AND product_status = '{_ESTATUS_PRODUCTO[m.group('est')]}'",
                  "Productos %s" % m.group("est"), "kpi_card", y="total_productos", etiqueta="Productos",
                  explicacion="Productos con ese estatus guardado (%s)." % _ESTATUS_PRODUCTO[m.group("est")])),

    (re.compile(r"^(?:cual es el |que )?tipo de (?:vale|incidencia) (?:es )?(?:el )?mas (?:frecuente|comun|usado)$"),
     lambda m: _d("SELECT t.incident_type_description AS tipo, COUNT(*) AS total FROM incident n "
                  "JOIN incident_type t ON t.id_incident_type = n.id_incident_type WHERE n.deletion_date IS NULL "
                  "GROUP BY t.incident_type_description ORDER BY total DESC LIMIT 1",
                  "Tipo de vale mas frecuente", "table")),

    # Vales creados en un periodo. `cuantos` y `cuantas`: la receta anterior solo aceptaba "cuantas".
    (re.compile(r"^cuant[oa]s (?:incidencias|vales) (?:se )?(?:registraron|hay|hubo|se crearon|se han creado|se han registrado|se hicieron) (?P<per>"
                + "|".join(_PERIODO) + r")$"),
     lambda m: _d(f"SELECT COUNT(*) AS total_periodo FROM incident WHERE deletion_date IS NULL "
                  f"AND incident_date >= date_trunc('{_PERIODO[m.group('per')]}', now())",
                  "Vales %s" % m.group("per"), "kpi_card", y="total_periodo", etiqueta="Vales")),

    (re.compile(r"^(?:top )?(?:las |los )?(?P<n>\d{1,2}) marcas con mas productos$"),
     lambda m: _d("SELECT b.brand_description AS marca, COUNT(*) AS total_productos FROM product p "
                  "JOIN brand b ON b.id_brand = p.id_marca WHERE p.deletion_date IS NULL "
                  "GROUP BY b.brand_description ORDER BY total_productos DESC LIMIT %d" % _n(m, 10),
                  "Top %d marcas con mas productos" % _n(m, 10), "bar", "marca", "total_productos")),

    (re.compile(r"^(?:que |cuales )?productos (?:tienen |hay con )?(?:menos de|menos que|por debajo de) (?P<n>\d{1,6}) existencias?$"),
     lambda m: _d(f"SELECT product_code AS codigo, descripcion AS producto, cantidad AS existencias {_EXIST} "
                  f"AND cantidad < {int(m.group('n'))} ORDER BY cantidad, descripcion",
                  "Productos con menos de %s existencias" % m.group("n"), "table")),

    (re.compile(r"^cuantos productos tienen (?:menos de|menos que|por debajo de) (?P<n>\d{1,6}) existencias?$"),
     lambda m: _d(f"SELECT COUNT(*) AS total_productos {_EXIST} AND cantidad < {int(m.group('n'))}",
                  "Productos con menos de %s existencias" % m.group("n"), "kpi_card", y="total_productos", etiqueta="Productos")),

    (re.compile(r"^(?:cual es el )?proyecto (?:con|de) mayor costo(?: total)?$"),
     lambda m: _d("SELECT title AS proyecto, total_cost AS costo_total FROM proyect WHERE deletion_date IS NULL "
                  "ORDER BY total_cost DESC NULLS LAST LIMIT 1", "Proyecto de mayor costo", "table")),

    (re.compile(r"^(?:cual es la )?factura (?:de|con) mayor (?:importe|monto|total)$"),
     lambda m: _d("SELECT folio, total, date_emision AS emision FROM invoice WHERE deletion_date IS NULL "
                  "ORDER BY total DESC NULLS LAST LIMIT 1", "Factura de mayor importe", "table")),

    # Misma definicion que "total facturado por cliente": todas las facturas vigentes.
    (re.compile(r"^(?:cual es el |cuanto es el )?total facturado$|^cuanto se ha facturado(?: en total)?$"),
     lambda m: _d("SELECT SUM(total) AS total_facturado FROM invoice WHERE deletion_date IS NULL",
                  "Total facturado", "kpi_card", y="total_facturado", etiqueta="Facturado",
                  explicacion="Suma del total de todas las facturas vigentes, sin importar su estatus.")),

    (re.compile(r"^(?:cuantas )?tareas (?:tiene cada proyecto|por proyecto|hay por proyecto)$"),
     lambda m: _d("SELECT p.title AS proyecto, COUNT(t.id_task) AS total_tareas FROM proyect p "
                  "LEFT JOIN task t ON t.id_proyect = p.id_proyect AND t.deletion_date IS NULL "
                  "WHERE p.deletion_date IS NULL GROUP BY p.id_proyect, p.title ORDER BY total_tareas DESC",
                  "Tareas por proyecto", "bar", "proyecto", "total_tareas")),

    (re.compile(r"^(?:cuantos )?proyectos (?:tiene cada cliente|por cliente|hay por cliente)$"),
     lambda m: _d("SELECT c.name AS cliente, COUNT(*) AS total_proyectos FROM proyect p "
                  "JOIN customer_supplier c ON c.id_customer_supplier = p.id_customer_supplier "
                  "WHERE p.deletion_date IS NULL GROUP BY c.name ORDER BY total_proyectos DESC",
                  "Proyectos por cliente", "bar", "cliente", "total_proyectos")),

    # --- Segunda ronda (b): lo que seguia sin receta en la bitacora real.
    (re.compile(r"^cuantos (?:usuarios|personas) no son empleados$"),
     lambda m: _d('SELECT COUNT(*) AS total_no_empleados FROM "user" WHERE deletion_date IS NULL '
                  "AND (is_employee = false OR is_employee IS NULL)",
                  "Usuarios que no son empleados", "kpi_card", y="total_no_empleados", etiqueta="No empleados")),

    # El rol se busca por nombre ("supervisor", "jefe de taller"), igual que material o marca.
    (re.compile(r"^cuantos usuarios (?:tienen|son|hay con) (?:el )?(?:rol|perfil|permiso) (?:de |como )?(?P<v>[a-z][a-z ]{1,38}?)$"),
     lambda m: _d('SELECT COUNT(*) AS total_usuarios FROM "user" u JOIN permission p ON p.id_permission = u.id_permission '
                  "WHERE u.deletion_date IS NULL AND p.permission_description ILIKE '%%%s%%'" % _comodin(m.group("v")),
                  "Usuarios con rol %s" % m.group("v").strip(), "kpi_card", y="total_usuarios", etiqueta="Usuarios")),

    (re.compile(r"^cuantos renglones de vales? (?:son |hay )?(?:de )?(?P<d>entrada|salida)$"),
     lambda m: _d("SELECT COUNT(*) AS total_renglones FROM nm_incident_product WHERE deletion_date IS NULL "
                  f"AND direction = '{m.group('d')}'", "Renglones de vale de %s" % m.group("d"), "kpi_card",
                  y="total_renglones", etiqueta="Renglones")),

    (re.compile(r"^cuantas herramientas (?:ya )?(?:fueron |han sido |estan )?devueltas$"),
     lambda m: _d("SELECT COUNT(*) AS devueltas FROM nm_incident_product WHERE deletion_date IS NULL AND close_date IS NOT NULL",
                  "Herramientas devueltas", "kpi_card", y="devueltas", etiqueta="Devueltas",
                  explicacion="Renglones de vales ya cerrados (con fecha de devolucion).")),

    (re.compile(r"^cuantos clientes distintos tienen proyectos$"),
     lambda m: _d("SELECT COUNT(DISTINCT id_customer_supplier) AS clientes_con_proyectos FROM proyect WHERE deletion_date IS NULL",
                  "Clientes con proyectos", "kpi_card", y="clientes_con_proyectos", etiqueta="Clientes")),

    (re.compile(r"^(?:cual es el )?cliente con mas proyectos$"),
     lambda m: _d("SELECT c.name AS cliente, COUNT(*) AS total_proyectos FROM proyect p "
                  "JOIN customer_supplier c ON c.id_customer_supplier = p.id_customer_supplier "
                  "WHERE p.deletion_date IS NULL GROUP BY c.name ORDER BY total_proyectos DESC LIMIT 1",
                  "Cliente con mas proyectos", "table")),

    (re.compile(r"^(?:cual es el )?costo total de (?:todos )?los proyectos$"),
     lambda m: _d("SELECT SUM(total_cost) AS costo_total FROM proyect WHERE deletion_date IS NULL",
                  "Costo total de los proyectos", "kpi_card", y="costo_total", etiqueta="Costo total",
                  explicacion="Suma del costo de los proyectos que ya lo tienen capturado.")),

    (re.compile(r"^(?:cual es el )?importe promedio de las facturas$"),
     lambda m: _d("SELECT AVG(total) AS importe_promedio FROM invoice WHERE deletion_date IS NULL",
                  "Importe promedio de las facturas", "kpi_card", y="importe_promedio", etiqueta="Promedio")),

    (re.compile(r"^(?:cuantas )?facturas (?:hay )?por moneda$"),
     lambda m: _d("SELECT currency AS moneda, COUNT(*) AS total_facturas FROM invoice WHERE deletion_date IS NULL "
                  "GROUP BY currency ORDER BY total_facturas DESC", "Facturas por moneda", "bar", "moneda", "total_facturas")),

    (re.compile(r"^cuantas facturas (?:se )?(?:emitieron|han emitido|hay|hubo) (?P<per>" + "|".join(_PERIODO) + r")$"),
     lambda m: _d(f"SELECT COUNT(*) AS total_periodo FROM invoice WHERE deletion_date IS NULL "
                  f"AND date_emision >= date_trunc('{_PERIODO[m.group('per')]}', now())",
                  "Facturas %s" % m.group("per"), "kpi_card", y="total_periodo", etiqueta="Facturas")),

    (re.compile(r"^(?:cual es )?la suma de las existencias(?: de todos los productos)?$"),
     lambda m: _d("SELECT SUM(cantidad) AS total_existencias FROM product WHERE deletion_date IS NULL",
                  "Total de existencias", "kpi_card", y="total_existencias", etiqueta="Existencias")),

    (re.compile(r"^cuantas marcas tienen productos(?: registrados)?$"),
     lambda m: _d(f"SELECT COUNT(DISTINCT id_marca) AS marcas_con_productos {_EXIST} AND id_marca IS NOT NULL",
                  "Marcas con productos", "kpi_card", y="marcas_con_productos", etiqueta="Marcas")),

    (re.compile(r"^cuantos (?:vales|incidencias) (?:se )?(?:crearon|registraron|hubo|hay) en los ultimos (?P<d>\d{1,3}) dias$"),
     lambda m: _d("SELECT COUNT(*) AS total_periodo FROM incident WHERE deletion_date IS NULL "
                  f"AND incident_date >= now() - interval '{int(m.group('d'))} days'",
                  "Vales de los ultimos %s dias" % m.group("d"), "kpi_card", y="total_periodo", etiqueta="Vales")),

    (re.compile(r"^(?:top )?(?P<n>\d{1,2}) ultimos vales(?: emitidos| creados)?$"),
     lambda m: _d("SELECT id_incident AS vale, incident_date AS fecha, incident_status AS estatus, external_folio AS folio "
                  "FROM incident WHERE deletion_date IS NULL ORDER BY incident_date DESC NULLS LAST LIMIT %d" % _n(m, 10),
                  "Ultimos %d vales" % _n(m, 10), "table")),

    (re.compile(r"^tabla (?:de|con)(?: los| todos los| todos)* (?:nombres de )?(?:todos )?(?:los )?(?P<ent>clientes|proyectos)$"),
     lambda m: _d("SELECT name AS cliente FROM customer_supplier WHERE deletion_date IS NULL ORDER BY name", "Clientes", "table")
     if m.group("ent") == "clientes" else
     _d("SELECT title AS proyecto, proyect_status AS estatus FROM proyect WHERE deletion_date IS NULL ORDER BY title",
        "Proyectos", "table")),

    (re.compile(r"^(?:que |cuales )?tipos de tarea (?:hay|existen)$"),
     lambda m: _d("SELECT task_type_description AS tipo FROM task_type WHERE deletion_date IS NULL ORDER BY 1",
                  "Tipos de tarea", "table")),

    (re.compile(r"^(?:cuantos )?proyectos (?:hay )?por prioridad$"),
     lambda m: _d("SELECT priority AS prioridad, COUNT(*) AS total_proyectos FROM proyect WHERE deletion_date IS NULL "
                  "GROUP BY priority ORDER BY total_proyectos DESC", "Proyectos por prioridad", "bar", "prioridad", "total_proyectos")),

    # Ordenes de compra: "monto total" es ambiguo (cotizado o autorizado; total_amount esta vacio), asi
    # que se muestran los dos, no se escoge uno en silencio. "Lo autorizado" si es una sola cifra.
    (re.compile(r"^(?:cual es el )?monto total de las ordenes de compra$"),
     lambda m: _d("SELECT SUM(quoted_total) AS cotizado, SUM(authorized_total) AS autorizado FROM purchase_order "
                  "WHERE deletion_date IS NULL", "Monto de las ordenes de compra", "table",
                  explicacion="Total cotizado y total autorizado de las ordenes de compra vigentes.")),

    (re.compile(r"^cuanto suma lo autorizado en ordenes de compra$|^(?:cual es )?el monto autorizado de las ordenes de compra$"),
     lambda m: _d("SELECT SUM(authorized_total) AS total_autorizado FROM purchase_order WHERE deletion_date IS NULL",
                  "Total autorizado en ordenes de compra", "kpi_card", y="total_autorizado", etiqueta="Autorizado")),

    (re.compile(r"^(?:cuantos )?materiales (?:hay )?por marca$"),
     lambda m: _d("SELECT b.brand_description AS marca, COUNT(*) AS total_materiales FROM material m "
                  "JOIN brand b ON b.id_brand = m.id_brand WHERE m.deletion_date IS NULL "
                  "GROUP BY b.brand_description ORDER BY total_materiales DESC",
                  "Materiales por marca", "bar", "marca", "total_materiales")),

]


# --- Recetas derivadas del ESQUEMA: "X por Y" y "X de este mes" para cualquier par que el esquema relacione.
# Las recetas fijas de arriba solo cubren lo que alguien escribio a mano (9 % de preguntas nuevas); estas
# salen de lo que el esquema ya sabe -- que FK une cada par y que columna lleva el nombre -- y se activan
# solo si TODO es inequivoco; ante cualquier duda se declinan y la pregunta sigue al modelo.
# Lo que dice el usuario -> tabla. Los identificadores del SQL salen de aqui y del esquema, nunca del texto.
_ENTIDADES = {
    "productos": "product", "materiales": "material", "vales": "incident", "incidencias": "incident",
    "proyectos": "proyect", "tareas": "task", "facturas": "invoice", "ordenes de compra": "purchase_order",
    "documentos": "document", "citas": "appointment", "tickets": "ticket", "contactos": "customer_contact",
    "renglones de vale": "nm_incident_product", "movimientos": "movement",
}
# Por que se agrupa: singular -> (tabla destino, pistas del nombre de la FK, en orden de preferencia).
_DIMENSIONES_ESQ = {
    "ubicacion": ("location", ()), "cliente": ("customer_supplier", ()), "proveedor": ("customer_supplier", ("proveedor", "supplier")),
    "proyecto": ("proyect", ()), "marca": ("brand", ()), "familia": ("product_family", ()),
    "departamento": ("department", ()), "material": ("material", ()),
    "responsable": ("user", ("id_user",)), "supervisor": ("user", ("supervisor",)), "lider": ("user", ("lider", "leader")),
    "usuario": ("user", ("id_user",)),
}
# Columna de fecha de cada tabla; si no esta aqui se usa creation_date (todas las tablas la traen).
_FECHA = {"incident": "incident_date", "invoice": "date_emision"}
_ENT_RE = "|".join(sorted(_ENTIDADES, key=len, reverse=True))
_X_POR_Y = re.compile(rf"^(?:cuantos |cuantas )?(?P<ent>{_ENT_RE}) (?:hay )?por (?P<dim>{'|'.join(_DIMENSIONES_ESQ)})$")
_X_PERIODO = re.compile(rf"^cuant[oa]s (?P<ent>{_ENT_RE}) (?:se )?(?:crearon|registraron|hay|hubo|se han creado|se han registrado) (?P<per>{'|'.join(_PERIODO)})$")


def _comillas(tabla):
    return f'"{tabla}"' if tabla == "user" else tabla     # `user` es palabra reservada


def _fk_hacia(relacion, destino, pistas):
    """La unica columna de `relacion` que apunta a `destino`, o None si hay cero o varias sin forma de elegir."""
    candidatas = [c for c in relacion.columnas if c.fk and str(c.fk).replace('"', "").split(".")[0].lower() == destino]
    if pistas:                                             # la pista manda: "supervisor" -> id_supervisor
        for pista in pistas:
            elegidas = [c for c in candidatas if pista in c.nombre.lower()]
            if len(elegidas) == 1:
                return elegidas[0]
        return None                                        # con pista y sin una unica coincidencia: duda, se declina
    exacta = [c for c in candidatas if c.nombre.lower() == f"id_{destino}"]
    if len(exacta) == 1:
        return exacta[0]
    return candidatas[0] if len(candidatas) == 1 else None


def _generica(texto: str, esquema) -> dict | None:
    from .schema_linking import _columna_nombre
    por_nombre = {r.nombre.lower(): r for r in esquema.relaciones}

    m = _X_POR_Y.search(texto)
    if m:
        ent = por_nombre.get(_ENTIDADES[m.group("ent")])
        destino_nombre, pistas = _DIMENSIONES_ESQ[m.group("dim")]
        destino = por_nombre.get(destino_nombre)
        fk = _fk_hacia(ent, destino_nombre, pistas) if ent and destino else None
        nombre = _columna_nombre(destino) if fk else None
        if fk is None or nombre is None:
            return None
        llave = str(fk.fk).replace('"', "").split(".")[-1] if "." in str(fk.fk) else f"id_{destino_nombre}"
        baja = " WHERE e.deletion_date IS NULL" if any(c.nombre.lower() == "deletion_date" for c in ent.columnas) else ""
        tot = f"total_{_alias(m.group('ent'))}"
        return _d(f"SELECT COALESCE(CAST(d.{nombre} AS TEXT), '(sin asignar)') AS {m.group('dim')}, COUNT(*) AS {tot} "
                  f"FROM {_comillas(ent.nombre)} e LEFT JOIN {_comillas(destino.nombre)} d ON d.{llave} = e.{fk.nombre}{baja} "
                  f"GROUP BY d.{nombre} ORDER BY {tot} DESC",
                  f"{m.group('ent').capitalize()} por {m.group('dim')}", "bar", m.group("dim"), tot,
                  explicacion=f"Cuenta de {m.group('ent')} agrupada por el {m.group('dim')} (campo {fk.nombre}).")

    m = _X_PERIODO.search(texto)
    if m:
        ent = por_nombre.get(_ENTIDADES[m.group("ent")])
        columnas = {c.nombre.lower() for c in ent.columnas} if ent else set()
        fecha = _FECHA.get(ent.nombre.lower(), "creation_date") if ent else None
        if ent is None or fecha not in columnas or "deletion_date" not in columnas:
            return None
        return _d(f"SELECT COUNT(*) AS total_periodo FROM {_comillas(ent.nombre)} WHERE deletion_date IS NULL "
                  f"AND {fecha} >= date_trunc('{_PERIODO[m.group('per')]}', now())",
                  f"{m.group('ent').capitalize()} {m.group('per')}", "kpi_card", y="total_periodo", etiqueta=m.group("ent").capitalize())
    return None


def buscar(pregunta: str, esquema=None) -> str | None:
    """El JSON de la directiva si la pregunta coincide con una receta, o None.

    Con `esquema`, si ninguna receta fija coincide, se prueba la receta derivada del esquema.
    """
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
    if esquema is not None:
        directiva = _generica(texto, esquema)
        if directiva:
            return json.dumps(directiva, ensure_ascii=False)
    return None
