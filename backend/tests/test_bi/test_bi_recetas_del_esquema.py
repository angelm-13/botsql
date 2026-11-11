"""Recetas derivadas del esquema: "X por Y" y "X de este mes" para cualquier par que el esquema relacione.

El esquema real se extrae de una base SQLite con llaves foraneas de verdad, asi que se prueba tambien que
la FK correcta se descubre (y que ante dos candidatas se declina en vez de adivinar).
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

    @event.listens_for(e, "before_cursor_execute", retval=True)
    def _ilike(conn, cursor, statement, parameters, context, executemany):
        return statement.replace(" ILIKE ", " LIKE "), parameters

    ddl = (
        'CREATE TABLE "user" (id_user INTEGER PRIMARY KEY, full_name TEXT, deletion_date TEXT)',
        "CREATE TABLE location (id_location INTEGER PRIMARY KEY, location_description TEXT, deletion_date TEXT)",
        "CREATE TABLE customer_supplier (id_customer_supplier INTEGER PRIMARY KEY, name TEXT, deletion_date TEXT)",
        "CREATE TABLE product (id_product INTEGER PRIMARY KEY, descripcion TEXT, "
        "id_location INTEGER REFERENCES location(id_location), deletion_date TEXT)",
        # dos FK hacia customer_supplier: el cliente (id_customer_supplier) y quien emite
        "CREATE TABLE invoice (id_invoice INTEGER PRIMARY KEY, total NUMERIC, date_emision TEXT, "
        "id_customer_supplier INTEGER REFERENCES customer_supplier(id_customer_supplier), "
        "id_issuer_customer_supplier INTEGER REFERENCES customer_supplier(id_customer_supplier), deletion_date TEXT)",
        # dos FK hacia "user": el responsable (id_user) y el lider (id_lider)
        "CREATE TABLE incident (id_incident INTEGER PRIMARY KEY, incident_date TEXT, "
        'id_user INTEGER REFERENCES "user"(id_user), id_lider INTEGER REFERENCES "user"(id_user), deletion_date TEXT)',
        "CREATE TABLE proyect (id_proyect INTEGER PRIMARY KEY, title TEXT, "
        'id_supervisor INTEGER REFERENCES "user"(id_user), deletion_date TEXT)',
        "CREATE TABLE document (id_document INTEGER PRIMARY KEY, title TEXT, creation_date TEXT, deletion_date TEXT)",
    )
    datos = (
        "INSERT INTO \"user\" VALUES (1, 'Ana', NULL), (2, 'Beto', NULL)",
        "INSERT INTO location VALUES (1, 'B1', NULL), (2, 'B2', NULL)",
        "INSERT INTO customer_supplier VALUES (1, 'A', NULL), (2, 'B', NULL)",
        # p1, p2 en B1; p3 en B2; p4 sin ubicacion; p5 en B1 pero dado de baja
        "INSERT INTO product (descripcion, id_location, deletion_date) VALUES "
        "('p1', 1, NULL), ('p2', 1, NULL), ('p3', 2, NULL), ('p4', NULL, NULL), ('p5', 1, '2026-01-01')",
        # facturas de A, A y B; TODAS las emite el cliente 2: si se usara la FK equivocada saldria B=3
        "INSERT INTO invoice (total, id_customer_supplier, id_issuer_customer_supplier, deletion_date) VALUES "
        "(10, 1, 2, NULL), (20, 1, 2, NULL), (30, 2, 2, NULL), (99, 1, 2, '2026-01-01')",
        # responsable Ana, Ana, Beto; lider Beto, Beto, Ana
        "INSERT INTO incident (id_user, id_lider, deletion_date) VALUES (1, 2, NULL), (1, 2, NULL), (2, 1, NULL), (1, 1, '2026-01-01')",
        "INSERT INTO proyect (title, id_supervisor, deletion_date) VALUES ('x', 1, NULL), ('y', 1, NULL), ('z', 2, NULL)",
        "INSERT INTO document (title, deletion_date) VALUES ('d1', NULL), ('d2', NULL)",
    )
    with e.begin() as c:
        for sentencia in ddl + datos:
            c.execute(text(sentencia))
    return e


@pytest.fixture(scope="module")
def entorno():
    e, aj = _motor(), AjustesBI()
    return e, aj, CacheDeEsquema(e, aj)


def _filas(entorno, pregunta):
    e, aj, cache = entorno
    r = service.responder(pregunta, engine=e, proveedor=SinModelo(), ajustes=aj, cache_esquema=cache)
    assert r.ok, (pregunta, r.error)
    return r.widgets[0].filas


def _por(entorno, pregunta, dim):
    return {list(f.values())[0]: list(f.values())[1] for f in _filas(entorno, pregunta)}  # por posicion: una receta fija puede llamar la columna distinto


def test_productos_por_ubicacion_cuenta_lo_vigente_y_los_sin_ubicacion(entorno):
    assert _por(entorno, "cuantos productos hay por ubicacion", "ubicacion") == {"B1": 2, "B2": 1, "(sin asignar)": 1}


def test_la_suma_del_desglose_es_el_total(entorno):
    assert sum(_por(entorno, "productos por ubicacion", "ubicacion").values()) == 4   # los vigentes, no el dado de baja


def test_facturas_por_cliente_usa_la_fk_del_cliente_y_no_la_del_emisor(entorno):
    assert _por(entorno, "facturas por cliente", "cliente") == {"A": 2, "B": 1}


def test_vales_por_responsable_y_por_lider_eligen_su_propia_fk(entorno):
    assert _por(entorno, "vales por responsable", "responsable") == {"Ana": 2, "Beto": 1}
    assert _por(entorno, "vales por lider", "lider") == {"Beto": 2, "Ana": 1}


def test_proyectos_por_supervisor(entorno):
    assert _por(entorno, "proyectos por supervisor", "supervisor") == {"Ana": 2, "Beto": 1}


@pytest.mark.parametrize("pregunta", [
    "facturas por proveedor",      # dos FK hacia customer_supplier y la pista no distingue: duda -> modelo
    "vales por supervisor",        # incident no tiene FK de supervisor
    "productos por cliente",       # product no se relaciona con customer_supplier
    "vales por ubicacion",
])
def test_ante_la_duda_se_declina_y_sigue_al_modelo(entorno, pregunta):
    assert recetas.buscar(pregunta, entorno[2].obtener()) is None


def test_sin_esquema_no_hay_receta_derivada(entorno):
    assert recetas.buscar("productos por ubicacion") is None


def test_el_periodo_arma_el_sql_con_la_fecha_de_la_tabla(entorno):
    esquema = entorno[2].obtener()
    sql = json.loads(recetas.buscar("cuantos documentos se crearon este mes", esquema))["sql_query"]
    assert "FROM document" in sql and "creation_date >= date_trunc('month', now())" in sql and "deletion_date IS NULL" in sql
    sql = json.loads(recetas.buscar("cuantos vales se crearon esta semana", esquema))["sql_query"]
    assert "incident_date >= date_trunc('week', now())" in sql        # el vale usa incident_date, no creation_date


def test_ninguna_receta_derivada_usa_limit_ni_texto_del_usuario(entorno):
    esquema = entorno[2].obtener()
    for p in ("productos por ubicacion", "facturas por cliente", "vales por responsable"):
        sql = json.loads(recetas.buscar(p, esquema))["sql_query"]
        assert "LIMIT" not in sql.upper() and p not in sql


def test_existencias_por_ubicacion_es_un_desglose_y_no_el_nombre_de_un_producto():
    # Hallazgo: la receta de "existencias de <producto>" leia "por ubicacion" como el nombre de un producto,
    # lo buscaba con ILIKE y devolvia vacio (una respuesta equivocada, peor que ir al modelo).
    sql = json.loads(recetas.buscar("existencias por ubicacion"))["sql_query"]
    assert "FROM inventory_stock" in sql and "GROUP BY l.location_description" in sql and "ILIKE" not in sql
    # y la de buscar un producto por su nombre sigue igual
    assert "ILIKE '%MARTILLO%'" in json.loads(recetas.buscar("existencias de martillo"))["sql_query"]
