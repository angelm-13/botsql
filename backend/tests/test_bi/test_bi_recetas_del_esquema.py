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
        "CREATE TABLE product_family (id_product_family INTEGER PRIMARY KEY, product_family_description TEXT, deletion_date TEXT)",
        # id_familia NO tiene FK real (como en la base de produccion): se reconoce como relacion logica
        "CREATE TABLE product (id_product INTEGER PRIMARY KEY, descripcion TEXT, id_familia INTEGER, "
        "id_location INTEGER REFERENCES location(id_location), deletion_date TEXT)",
        # dos FK hacia customer_supplier: el cliente (id_customer_supplier) y quien emite
        "CREATE TABLE invoice (id_invoice INTEGER PRIMARY KEY, total NUMERIC, date_emision TEXT, "
        "id_customer_supplier INTEGER REFERENCES customer_supplier(id_customer_supplier), "
        "id_issuer_customer_supplier INTEGER REFERENCES customer_supplier(id_customer_supplier), deletion_date TEXT)",
        # dos FK hacia "user": el responsable (id_user) y el lider (id_lider)
        "CREATE TABLE incident (id_incident INTEGER PRIMARY KEY, incident_date TEXT, "
        'id_user INTEGER REFERENCES "user"(id_user), id_lider INTEGER REFERENCES "user"(id_user), deletion_date TEXT)',
        "CREATE TABLE proyect (id_proyect INTEGER PRIMARY KEY, title TEXT, creation_date TEXT, "
        "id_customer_supplier INTEGER REFERENCES customer_supplier(id_customer_supplier), "
        'id_supervisor INTEGER REFERENCES "user"(id_user), deletion_date TEXT)',
        "CREATE TABLE task (id_task INTEGER PRIMARY KEY, id_proyect INTEGER REFERENCES proyect(id_proyect), "
        "task_status TEXT, deletion_date TEXT)",
        "CREATE TABLE appointment (id_appointment INTEGER PRIMARY KEY, appointment_status TEXT, creation_date TEXT, deletion_date TEXT)",
        "CREATE TABLE document (id_document INTEGER PRIMARY KEY, title TEXT, creation_date TEXT, deletion_date TEXT)",
    )
    datos = (
        "INSERT INTO \"user\" VALUES (1, 'Ana', NULL), (2, 'Beto', NULL)",
        "INSERT INTO location VALUES (1, 'B1', NULL), (2, 'B2', NULL)",
        "INSERT INTO customer_supplier VALUES (1, 'A', NULL), (2, 'B', NULL), (3, 'C', NULL)",   # C no tiene proyectos ni facturas
        "INSERT INTO product_family VALUES (1, 'F1', NULL), (2, 'F2', NULL)",
        # p1, p2 en B1 y familia F1; p3 en B2 y F2; p4 sin ubicacion ni familia; p5 en B1 pero dado de baja
        "INSERT INTO product (descripcion, id_location, id_familia, deletion_date) VALUES "
        "('p1', 1, 1, NULL), ('p2', 1, 1, NULL), ('p3', 2, 2, NULL), ('p4', NULL, NULL, NULL), ('p5', 1, 1, '2026-01-01')",
        # facturas de A, A y B; TODAS las emite el cliente 2: si se usara la FK equivocada saldria B=3
        "INSERT INTO invoice (total, id_customer_supplier, id_issuer_customer_supplier, deletion_date) VALUES "
        "(10, 1, 2, NULL), (20, 1, 2, NULL), (30, 2, 2, NULL), (99, 1, 2, '2026-01-01')",
        # responsable Ana, Ana, Beto; lider Beto, Beto, Ana
        # el mas reciente VIGENTE es el 1 (2026-01-03); el 4 es mas nuevo pero esta dado de baja
        "INSERT INTO incident (id_user, id_lider, incident_date, deletion_date) VALUES "
        "(1, 2, '2026-01-03', NULL), (1, 2, '2026-01-02', NULL), (2, 1, '2026-01-01', NULL), (1, 1, '2026-01-04', '2026-01-09')",
        # x, y del cliente A; z del B. Tareas: dos para x; una (dada de baja) para y; ninguna para z
        "INSERT INTO proyect (title, creation_date, id_customer_supplier, id_supervisor, deletion_date) VALUES "
        "('x', '2026-01-15', 1, 1, NULL), ('y', '2026-01-20', 1, 1, NULL), ('z', '2026-02-03', 2, 2, NULL)",
        "INSERT INTO task (id_proyect, task_status, deletion_date) VALUES (1, 'a', NULL), (1, 'b', NULL), (2, 'a', '2026-01-09')",
        "INSERT INTO appointment (appointment_status, deletion_date) VALUES ('pendiente', NULL), ('confirmada', NULL), ('pendiente', NULL), ('pendiente', '2026-01-09')",
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


# --- Mas formas de pregunta: sin hijos, el mas reciente, top N, por estatus/tiempo, relacion logica ------------------

def _lista(entorno, pregunta):
    return sorted(list(f.values())[0] for f in _filas(entorno, pregunta))


def test_padres_sin_hijos_no_cuentan_a_los_dados_de_baja(entorno):
    # y tiene una unica tarea y esta dada de baja: para efectos practicos no tiene tareas
    assert _lista(entorno, "proyectos sin tareas") == ["y", "z"]
    assert list(_filas(entorno, "cuantos proyectos sin tareas")[0].values())[0] == 2
    assert _lista(entorno, "clientes sin proyectos") == ["C"]
    assert _lista(entorno, "clientes sin facturas") == ["C"]       # con dos FK hacia customer_supplier, la del cliente


def test_el_mas_reciente_ignora_lo_dado_de_baja(entorno):
    for pregunta in ("ultimo vale", "vale mas reciente"):
        fila = _filas(entorno, pregunta)[0]
        assert list(fila.values())[0] == 1 and "2026-01-03" in str(fila["incident_date"]), pregunta   # no el 4 (de baja)


def test_top_n_de_una_dimension_no_cuenta_los_sin_asignar(entorno):
    assert [(f["cliente"], list(f.values())[1]) for f in _filas(entorno, "los 2 clientes con mas facturas")] == [("A", 2), ("B", 1)]
    una = _filas(entorno, "cual es el cliente con mas facturas")
    assert [(f["cliente"], list(f.values())[1]) for f in una] == [("A", 2)]


def test_por_estatus_se_deriva_de_la_columna_de_estatus_de_la_tabla(entorno):
    assert _por(entorno, "citas por estatus", "estatus") == {"pendiente": 2, "confirmada": 1}


def test_una_relacion_logica_sin_fk_real_tambien_se_reconoce(entorno):
    # product.id_familia no tiene llave foranea (como en produccion) pero el modelo de datos la usa
    assert _por(entorno, "cuantos productos hay por familia", "familia") == {"F1": 2, "F2": 1, "(sin asignar)": 1}


@pytest.mark.parametrize("pregunta,trozo", [
    ("vales por mes", "date_trunc('month', incident_date)"),
    ("vales por dia", "date_trunc('day', incident_date)"),
    ("proyectos por anio", "date_trunc('year', creation_date)"),
])
def test_por_tiempo_usa_la_fecha_de_la_tabla(entorno, pregunta, trozo):
    assert trozo in json.loads(recetas.buscar(pregunta, entorno[2].obtener()))["sql_query"]


@pytest.mark.parametrize("pregunta", [
    # En los datos reales "sin marca"/"sin ubicacion" NO es NULL sino una fila centinela ("Sin marca especifica"):
    # un IS NULL daria 0 y seria una respuesta enganosa, asi que se dejan al modelo.
    "productos sin ubicacion", "productos sin familia", "cuantos productos tienen familia", "tareas sin proyecto",
    "los 3 clientes con mas productos",     # product no se relaciona con customer_supplier
])
def test_lo_que_depende_de_que_significa_sin_se_declina(entorno, pregunta):
    assert recetas.buscar(pregunta, entorno[2].obtener()) is None
