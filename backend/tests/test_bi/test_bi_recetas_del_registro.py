"""Recetas que salen de la bitacora real (`bi_query_log`): preguntas que fallaban o tardaban minutos.

Cada pregunta se ejecuta de punta a punta sobre SQLite con datos calculados a mano; las que usan funciones
propias de Postgres (date_trunc, interval) se comprueban solo por el SQL que arman y se verificaron aparte
contra la base real.
"""

import json

import pytest
from sqlalchemy import create_engine, event, text

from app.bi import recetas, service
from app.bi.config import AjustesBI
from app.bi.llm_provider import ProveedorLLM, ProveedorNoDisponible
from app.bi.schema_extractor import CacheDeEsquema


class SinModelo(ProveedorLLM):
    def generar(self, prompt, pregunta="", formato=None):
        raise ProveedorNoDisponible("el modelo no debe usarse")

    def disponible(self):
        return False


def _motor():
    e = create_engine("sqlite://")

    # SQLite no tiene ILIKE (es de Postgres); su LIKE ya ignora mayusculas en ASCII, que es lo que se prueba.
    @event.listens_for(e, "before_cursor_execute", retval=True)
    def _ilike(conn, cursor, statement, parameters, context, executemany):
        return statement.replace(" ILIKE ", " LIKE "), parameters

    ddl = (
        "CREATE TABLE brand (id_brand INTEGER PRIMARY KEY, brand_description TEXT, deletion_date TEXT)",
        "CREATE TABLE product (id_product INTEGER PRIMARY KEY, product_code TEXT, descripcion TEXT, cantidad INTEGER, "
        "id_marca INTEGER, product_status TEXT, deletion_date TEXT)",
        "CREATE TABLE product_family (id_product_family INTEGER PRIMARY KEY, product_family_description TEXT, deletion_date TEXT)",
        "CREATE TABLE department (id_department INTEGER PRIMARY KEY, department_description TEXT, deletion_date TEXT)",
        "CREATE TABLE document (id_document INTEGER PRIMARY KEY, status TEXT, deletion_date TEXT)",
        "CREATE TABLE purchase_order (id_purchase_order INTEGER PRIMARY KEY, order_status TEXT, quoted_total NUMERIC, "
        "authorized_total NUMERIC, deletion_date TEXT)",
        "CREATE TABLE customer_supplier (id_customer_supplier INTEGER PRIMARY KEY, name TEXT, deletion_date TEXT)",
        "CREATE TABLE proyect (id_proyect INTEGER PRIMARY KEY, title TEXT, total_cost NUMERIC, proyect_status TEXT, "
        "priority TEXT, id_customer_supplier INTEGER, deletion_date TEXT)",
        "CREATE TABLE task (id_task INTEGER PRIMARY KEY, id_proyect INTEGER, task_status TEXT, deletion_date TEXT)",
        "CREATE TABLE task_type (id_task_type INTEGER PRIMARY KEY, task_type_description TEXT, deletion_date TEXT)",
        "CREATE TABLE incident_type (id_incident_type INTEGER PRIMARY KEY, incident_type_description TEXT, deletion_date TEXT)",
        "CREATE TABLE incident (id_incident INTEGER PRIMARY KEY, incident_date TEXT, incident_status TEXT, "
        "id_incident_type INTEGER, external_folio TEXT, deletion_date TEXT)",
        "CREATE TABLE nm_incident_product (id INTEGER PRIMARY KEY, direction TEXT, close_date TEXT, deletion_date TEXT)",
        "CREATE TABLE invoice (id_invoice INTEGER PRIMARY KEY, folio TEXT, total NUMERIC, date_emision TEXT, "
        "currency TEXT, invoice_status TEXT, deletion_date TEXT)",
        "CREATE TABLE permission (id_permission INTEGER PRIMARY KEY, permission_description TEXT)",
        'CREATE TABLE "user" (id_user INTEGER PRIMARY KEY, full_name TEXT, is_employee BOOLEAN, id_permission INTEGER, deletion_date TEXT)',
    )
    datos = (
        "INSERT INTO brand VALUES (1, 'Marca1', NULL), (2, 'Marca2', NULL), (3, 'Marca3', NULL)",
        # a, b extraviados con 0; c igual pero dado de baja; d danado sin dato; e entrada con 5; f salida con 20
        "INSERT INTO product (descripcion, cantidad, id_marca, product_status, deletion_date) VALUES "
        "('a', 0, 1, 'EXTRAVIADO', NULL), ('b', 0, 1, 'EXTRAVIADO', NULL), ('c', 0, 1, 'EXTRAVIADO', '2026-01-01'), "
        "('d', NULL, 2, 'DAÑADO', NULL), ('e', 5, 1, 'ENTRADA', NULL), ('f', 20, NULL, 'SALIDA', NULL)",
        "INSERT INTO product_family VALUES (1, 'F1', NULL), (2, 'F2', NULL), (3, 'F3', '2026-01-01')",
        "INSERT INTO department VALUES (1, 'D1', NULL), (2, 'D2', '2026-01-01')",
        "INSERT INTO document (status, deletion_date) VALUES ('issued', NULL), ('issued', NULL), ('issued', '2026-01-01')",
        "INSERT INTO purchase_order (order_status, quoted_total, authorized_total, deletion_date) VALUES "
        "('authorized', 100, 80, NULL), ('pending_authorization', 200, NULL, NULL), ('authorized', 50, 50, '2026-01-01')",
        "INSERT INTO customer_supplier VALUES (1, 'Cliente A', NULL), (2, 'Cliente B', NULL), (3, 'Baja', '2026-01-01')",
        "INSERT INTO proyect (title, total_cost, proyect_status, priority, id_customer_supplier, deletion_date) VALUES "
        "('Alfa', 100, 'in_progress', 'alta', 1, NULL), ('Beta', 500, 'denied', 'media', 1, NULL), "
        "('Gama', NULL, 'collected', NULL, 2, NULL), ('Zeta', 9999, 'denied', 'alta', 1, '2026-01-01')",
        "INSERT INTO task (id_proyect, task_status, deletion_date) VALUES (1, 'pendiente', NULL), (1, 'terminada', NULL), (2, 'pendiente', NULL)",
        "INSERT INTO task_type (task_type_description, deletion_date) VALUES ('Soldar', NULL), ('Pintar', NULL), ('Viejo', '2026-01-01')",
        "INSERT INTO incident_type VALUES (1, 'Prestamo', NULL), (2, 'Reparacion', NULL)",
        "INSERT INTO incident (incident_date, incident_status, id_incident_type, external_folio, deletion_date) VALUES "
        "('2026-01-03', 'abierta', 1, 'X3', NULL), ('2026-01-02', 'abierta', 1, 'X2', NULL), "
        "('2026-01-01', 'cerrada', 2, 'X1', NULL), ('2026-01-04', 'abierta', 2, 'X4', '2026-01-09')",
        "INSERT INTO nm_incident_product (direction, close_date, deletion_date) VALUES "
        "('salida', NULL, NULL), ('salida', NULL, NULL), ('entrada', '2026-02-02', NULL), ('salida', NULL, '2026-01-01')",
        "INSERT INTO invoice (folio, total, date_emision, currency, invoice_status, deletion_date) VALUES "
        "('F1', 100, '2026-01-01', 'MXN', 'pendiente', NULL), ('F2', 50, '2026-01-02', 'USD', 'pendiente', NULL), "
        "('F3', 999, '2026-01-03', 'MXN', 'captura', '2026-01-09')",
        "INSERT INTO permission VALUES (1, 'Supervisor'), (2, 'Almacenista')",
        'INSERT INTO "user" (full_name, is_employee, id_permission, deletion_date) VALUES '
        "('u1', 1, 1, NULL), ('u2', 0, 2, NULL), ('u3', NULL, 1, NULL), ('u4', 0, 2, '2026-01-01')",
    )
    with e.begin() as c:
        for sentencia in ddl + datos:
            c.execute(text(sentencia))
    return e


def _filas(pregunta):
    e, aj = _motor(), AjustesBI()
    r = service.responder(pregunta, engine=e, proveedor=SinModelo(), ajustes=aj, cache_esquema=CacheDeEsquema(e, aj))
    assert r.ok, (pregunta, r.error)
    return r.widgets[0].filas


def _valor(pregunta):
    return list(_filas(pregunta)[0].values())[0]


# (pregunta, valor de la primera celda) -- calculado a mano de los datos de arriba
CIFRAS = [
    ("cuantos productos estan extraviados", 2), ("cuantos productos estan danados", 1),
    ("cuantos productos tienen menos de 10 existencias", 3),
    ("cuantas marcas tienen productos registrados", 2),
    ("cuantas familias de producto existen", 2), ("cuantas marcas de herramientas hay registradas", 3),
    ("cuantos departamentos hay", 1), ("cuantos documentos hay registrados", 2),
    ("cuantas ordenes de compra hay", 2), ("cuantas ordenes de compra estan autorizadas", 1),
    ("cuantos clientes y proveedores hay", 2), ("cuantos renglones de vale hay", 3),
    ("cuantos tipos de vale existen", 2), ("cuantos renglones de vale son de salida", 2),
    ("cuantas herramientas ya fueron devueltas", 1),
    ("cuantos usuarios no son empleados", 2), ("cuantos usuarios tienen el rol de supervisor", 2),
    ("cuantos proyectos tienen de estado denegado", 1), ("cuantos proyectos se encuentran como recolectados", 1),
    ("cuantos proyectos se tienen de estado recolectado", 1), ("cuantos proyectos estan en proceso", 1),
    ("cuantos clientes distintos tienen proyectos", 2),
    ("cual es el costo total de todos los proyectos", 600),
    ("cual es el total facturado", 150), ("cual es el importe promedio de las facturas", 75),
    ("cual es la suma de las existencias de todos los productos", 25),
    ("cuanto suma lo autorizado en ordenes de compra", 80),
]


@pytest.mark.parametrize("pregunta,esperado", CIFRAS)
def test_la_cifra_sale_sin_modelo_y_es_la_correcta(pregunta, esperado):
    assert _valor(pregunta) == esperado, pregunta


def test_los_renglones_pendientes_y_devueltos_suman_todos_los_renglones():
    assert _valor("cuantas herramientas estan pendientes de devolver") + _valor("cuantas herramientas ya fueron devueltas") \
        == _valor("cuantos renglones de vale hay")


def test_desgloses_por_estatus():
    def por(pregunta):
        return {f["estatus"]: list(f.values())[1] for f in _filas(pregunta)}
    assert por("cuantos productos hay por estatus") == {"EXTRAVIADO": 2, "DAÑADO": 1, "ENTRADA": 1, "SALIDA": 1}
    assert por("cuantas ordenes de compra hay por estatus") == {"authorized": 1, "pending_authorization": 1}
    assert por("cuantos documentos hay por estatus") == {"issued": 2}


def test_vales_de_cada_tipo_y_tipo_mas_frecuente():
    assert {f["tipo"]: list(f.values())[1] for f in _filas("cuantos vales hay de cada tipo")} == {"Prestamo": 2, "Reparacion": 1}
    assert _filas("cual es el tipo de vale mas frecuente")[0]["tipo"] == "Prestamo"


def test_clientes_proyectos_y_tareas():
    assert {f["cliente"]: f["total_proyectos"] for f in _filas("cuantos proyectos tiene cada cliente")} == {"Cliente A": 2, "Cliente B": 1}
    assert _filas("cual es el cliente con mas proyectos")[0]["cliente"] == "Cliente A"
    # LEFT JOIN: un proyecto sin tareas aparece con 0, y el dado de baja no aparece
    assert {f["proyecto"]: f["total_tareas"] for f in _filas("cuantas tareas tiene cada proyecto")} == {"Alfa": 2, "Beta": 1, "Gama": 0}
    assert _filas("cual es el proyecto con mayor costo total")[0]["proyecto"] == "Beta"
    assert {f["prioridad"]: f["total_proyectos"] for f in _filas("cuantos proyectos hay por prioridad")} == {"alta": 1, "media": 1, None: 1}


def test_marcas_existencias_y_ultimos_vales():
    marcas = _filas("una grafica de las 2  marcas con mas productos")
    assert [(f["marca"], f["total_productos"]) for f in marcas] == [("Marca1", 3), ("Marca2", 1)]
    bajas = _filas("que productos tienen menos de 10 existencias")
    assert [f["producto"] for f in bajas] == ["a", "b", "e"]          # el NULL y el dado de baja no entran
    assert [f["vale"] for f in _filas("top 2 ultimos vales")] == [1, 2]  # por fecha descendente, sin el dado de baja


def test_facturas_ordenes_y_listas():
    assert _filas("cual es la factura de mayor importe")[0]["folio"] == "F1"
    assert {f["moneda"]: f["total_facturas"] for f in _filas("cuantas facturas hay por moneda")} == {"MXN": 1, "USD": 1}
    monto = _filas("cual es el monto total de las ordenes de compra")[0]
    assert (monto["cotizado"], monto["autorizado"]) == (300, 80)       # los dos: "total" es ambiguo
    assert sorted(f["cliente"] for f in _filas("tabla de clientes")) == ["Cliente A", "Cliente B"]
    assert len(_filas("tabla con todos los nombres de todos los proyectos")) == 3
    assert sorted(f["tipo"] for f in _filas("que tipos de tarea hay?")) == ["Pintar", "Soldar"]


# --- Lo que usa funciones de Postgres: solo se comprueba el SQL (se ejecuto aparte contra la base real) ----------

@pytest.mark.parametrize("pregunta,trozo", [
    ("cuantos vales se crearon este anio", "date_trunc('year', now())"),
    ("cuantos vales se crearon este mes", "date_trunc('month', now())"),
    ("cuantos vales se crearon en los ultimos 30 dias", "interval '30 days'"),
    ("cuantas facturas se emitieron este anio", "date_trunc('year', now())"),
    ("cuanto se ha facturado por mes", "date_trunc('month', date_emision)"),
])
def test_los_periodos_arman_el_sql_correcto(pregunta, trozo):
    assert trozo in json.loads(recetas.buscar(pregunta))["sql_query"]


@pytest.mark.parametrize("pregunta", [
    "cuantos documentos estan vencidos",          # la tabla document no tiene fecha de vencimiento
    "cuantos productos son desarmador",           # descripcion o material? lo define el negocio
    "grafica de proyectos comparando a que clientes",
    "cuantas facturas estan canceladas",          # estatus que no existe en los datos reales
])
def test_lo_que_no_tiene_una_respuesta_unica_sigue_al_modelo(pregunta):
    assert recetas.buscar(pregunta) is None


@pytest.mark.parametrize("pregunta", ["cuantos usuarios tienen el rol de x'; DROP TABLE \"user\"; --",
                                      "cuantos renglones de vale son de salida' OR '1'='1"])
def test_nada_de_lo_escrito_llega_al_sql_sin_limpiar(pregunta):
    r = recetas.buscar(pregunta)
    if r is not None:  # lo que no sea [a-z0-9 ] se descarta o no coincide
        assert "DROP" not in json.loads(r)["sql_query"].upper() and "'1'='1'" not in json.loads(r)["sql_query"]
