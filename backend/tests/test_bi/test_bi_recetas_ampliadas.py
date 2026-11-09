"""Recetas ampliadas: formas naturales de preguntar lo mismo se resuelven sin el modelo, con el
resultado correcto, y lo ambiguo NO se contesta en silencio."""

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

    with e.begin() as c:
        for ddl in (
            "CREATE TABLE brand (id_brand INTEGER PRIMARY KEY, brand_description TEXT)",
            "CREATE TABLE material (id_material INTEGER PRIMARY KEY, material_description TEXT, id_brand INTEGER, deletion_date TEXT)",
            "CREATE TABLE product_family (id_product_family INTEGER PRIMARY KEY, product_family_description TEXT)",
            "CREATE TABLE location (id_location INTEGER PRIMARY KEY, location_description TEXT)",
            "CREATE TABLE product (id_product INTEGER PRIMARY KEY, product_code TEXT, descripcion TEXT, cantidad INTEGER, "
            "id_marca INTEGER REFERENCES brand(id_brand), id_material INTEGER REFERENCES material(id_material), "
            "id_familia INTEGER REFERENCES product_family(id_product_family), id_location INTEGER REFERENCES location(id_location), deletion_date TEXT)",
            "CREATE TABLE incident (id_incident INTEGER PRIMARY KEY, incident_status TEXT, id_incident_type INTEGER, id_user INTEGER, deletion_date TEXT)",
            "CREATE TABLE incident_type (id_incident_type INTEGER PRIMARY KEY, incident_type_description TEXT)",
            "CREATE TABLE proyect (id_proyect INTEGER PRIMARY KEY, proyect_status TEXT, deletion_date TEXT)",
            "CREATE TABLE task (id_task INTEGER PRIMARY KEY, task_status TEXT, deletion_date TEXT)",
            "CREATE TABLE invoice (id_invoice INTEGER PRIMARY KEY, invoice_status TEXT, total NUMERIC, deletion_date TEXT)",
            'CREATE TABLE "user" (id_user INTEGER PRIMARY KEY, full_name TEXT, deletion_date TEXT)',
            "CREATE TABLE nm_incident_product (id INTEGER PRIMARY KEY, close_date TEXT, deletion_date TEXT)",
        ):
            c.execute(text(ddl))
        # productos: dos agotados vigentes, uno agotado dado de baja, uno con NULL, dos con existencia
        c.execute(text("INSERT INTO product (descripcion, cantidad, deletion_date) VALUES "
                       "('a', 0, NULL), ('b', 0, NULL), ('c', 0, '2026-01-01'), ('d', NULL, NULL), ('e', 5, NULL), ('f', 20, NULL)"))
        c.execute(text("INSERT INTO brand VALUES (1, 'Marca1'), (2, 'Marca2')"))
        c.execute(text("INSERT INTO material (id_material, material_description, id_brand, deletion_date) VALUES "
                       "(1, 'DESARMADOR PLANO', 1, NULL), (2, 'DESARMADOR DE CRUZ GRANDE', 1, NULL), "
                       "(3, 'MARTILLO', 2, NULL), (4, 'OTRO', 2, '2026-01-01')"))
        c.execute(text("INSERT INTO product_family VALUES (1, 'HERRAMIENTA MANUAL')"))
        c.execute(text("INSERT INTO location VALUES (1, 'ALMACEN GENERAL')"))
        # a, b -> DESARMADOR PLANO; c (dado de baja) tambien; d -> DESARMADOR DE CRUZ GRANDE; e -> MARTILLO; f sin material
        c.execute(text("UPDATE product SET id_material = 1, id_marca = 1, id_familia = 1, id_location = 1 WHERE descripcion IN ('a', 'b', 'c')"))
        c.execute(text("UPDATE product SET id_material = 2, id_marca = 2 WHERE descripcion = 'd'"))
        c.execute(text("UPDATE product SET id_material = 3 WHERE descripcion = 'e'"))
        c.execute(text("INSERT INTO incident (incident_status, deletion_date) VALUES ('abierta', NULL), ('abierta', NULL), ('cerrada', NULL), ('abierta', '2026-01-01')"))
        c.execute(text("INSERT INTO proyect (proyect_status, deletion_date) VALUES ('in_progress', NULL), ('in_progress', NULL), ('draft', NULL), ('authorized', '2026-01-01')"))
        c.execute(text("INSERT INTO task (task_status, deletion_date) VALUES ('pendiente', NULL), ('terminada', NULL), ('pendiente', NULL)"))
        c.execute(text("INSERT INTO invoice (invoice_status, total, deletion_date) VALUES ('timbrada', 100, NULL), ('cancelada', 50, NULL)"))
        c.execute(text('INSERT INTO "user" (full_name, deletion_date) VALUES (\'u1\', NULL), (\'u2\', NULL), (\'u3\', \'2026-01-01\')'))
        c.execute(text("INSERT INTO nm_incident_product (close_date, deletion_date) VALUES (NULL, NULL), (NULL, NULL), ('2026-02-02', NULL), (NULL, '2026-01-01')"))
    return e


def _responder(pregunta):
    e, aj = _motor(), AjustesBI()
    return service.responder(pregunta, engine=e, proveedor=SinModelo(), ajustes=aj,
                             cache_esquema=CacheDeEsquema(e, aj))


def _unico(r):
    assert r.ok, r.error
    return r.widgets[0].filas


# (pregunta, valor esperado en la primera celda del primer renglon) -- calculado a mano de los datos de arriba
TOTALES = [
    ("cuántos vales hay", 3), ("cuantas incidencias hay", 3), ("cuántos proyectos hay", 3),
    ("cuántos usuarios hay", 2), ("cuántos materiales hay", 3), ("cuántas tareas hay", 3),
    ("cuántas facturas hay", 2), ("número de productos", 5), ("cuántos artículos hay", 5),
    ("total de vales", 3), ("cuántos productos hay en total", 5),
    ("cuántos productos están agotados", 2), ("cuántos productos tienen existencias en cero", 2),
    ("cuántos productos sin existencias hay", 2),
    ("cuántas herramientas están pendientes de devolver", 2),
    ("cuántos vales abiertos hay", 2), ("vales abiertos", 2), ("tareas pendientes", 2),
    ("proyectos en proceso", 2), ("cuántos proyectos están en proceso", 2), ("proyectos en borrador", 1),
]


@pytest.mark.parametrize("pregunta,esperado", TOTALES)
def test_el_conteo_sale_sin_modelo_y_es_el_correcto(pregunta, esperado):
    fila = _unico(_responder(pregunta))[0]
    assert list(fila.values())[0] == esperado, fila


def test_los_desgloses_por_estatus_y_marca_cuentan_lo_vigente():
    est = {f["estatus"]: list(f.values())[1] for f in _unico(_responder("cuántos vales hay por estatus"))}
    assert est == {"abierta": 2, "cerrada": 1}
    assert {f["estatus"]: list(f.values())[1] for f in _unico(_responder("tareas por estatus"))} == {"pendiente": 2, "terminada": 1}
    assert {f["estatus"]: list(f.values())[1] for f in _unico(_responder("facturas por estatus"))} == {"timbrada": 1, "cancelada": 1}
    assert {f["marca"]: f["total_materiales"] for f in _unico(_responder("materiales por marca"))} == {"Marca1": 2, "Marca2": 1}


def test_producto_con_mas_y_con_menos_existencias_ignora_nulos_y_bajas():
    assert _unico(_responder("cuál es el producto con más existencias"))[0]["producto"] == "f"
    assert _unico(_responder("producto con menos existencias"))[0]["existencias"] == 0
    top = _unico(_responder("top 2 productos con menos existencias"))
    assert len(top) == 2 and all(f["existencias"] == 0 for f in top)


def test_la_lista_de_agotados_no_trae_bajas_ni_nulos():
    assert sorted(f["producto"] for f in _unico(_responder("productos agotados"))) == ["a", "b"]


@pytest.mark.parametrize("pregunta", [
    "cuántos vales hay por estatus", "vales por tipo", "vales por responsable", "marcas con más productos",
    "cuántos vales hay", "tareas por estatus", "facturas por estatus", "productos agotados",
])
def test_las_frases_nuevas_las_resuelve_una_receta(pregunta):
    assert recetas.buscar(pregunta) is not None


@pytest.mark.parametrize("pregunta", [
    # Ambiguas: "activo", "valor", "total facturado" (¿incluye canceladas?) las define el negocio, no una receta.
    # ("total facturado" y "proyectos por cliente" salieron de esta lista en la segunda ronda: son preguntas reales
    # y repetidas de la bitacora, con la misma definicion que las recetas que ya existian.)
    "proyectos activos", "valor del inventario", "facturado este mes", "usuarios activos",
    "facturas pendientes de pago", "herramientas prestadas",
])
def test_lo_ambiguo_sigue_yendo_al_modelo(pregunta):
    assert recetas.buscar(pregunta) is None


def test_ninguna_receta_nueva_usa_limit_sin_que_se_pida_un_top():
    # Regla del prompt: LIMIT solo con "top N" (un LIMIT de mas trunca agrupaciones).
    for p in ("cuántos vales hay por estatus", "tareas por estatus", "facturas por estatus", "materiales por marca",
              "productos agotados", "cuántos usuarios hay"):
        assert "LIMIT" not in json.loads(recetas.buscar(p))["sql_query"].upper(), p


# --- Dependencias que el usuario dice en espanol ("ID Material desarmador") --------------------------------

DEPENDENCIAS = [
    # Datos del fixture: material 1 'DESARMADOR PLANO' <- a, b, c(dado de baja); material 2 'DESARMADOR DE CRUZ
    # GRANDE' <- d; material 3 'MARTILLO' <- e. Marca1 <- a, b, c(baja); familia y ubicacion 1 <- a, b, c(baja).
    # El caso reportado: los nombres estan en mayusculas y son mas largos que lo que se dice.
    ("cuantos productos tienen como ID Material \"desarmador\"?", 3),     # a, b (de PLANO) + d (de CRUZ)
    ("cuantos productos tienen como id material 'desarmador'", 3),
    ("cuantos productos tienen el material desarmador plano", 2),         # a, b
    ("cuantos productos tienen material desarmador cruz", 1),             # d: '%DESARMADOR%CRUZ%'
    ("cuantos productos tienen material martillo", 1),                    # e
    ("cuantos productos son de la marca marca1", 2),                      # a, b
    ("cuantos productos tienen familia herramienta", 2),                  # a, b
    ("cuantos productos estan en ubicacion almacen general", 2),          # a, b
]


@pytest.mark.parametrize("pregunta,esperado", DEPENDENCIAS)
def test_un_producto_se_busca_por_el_nombre_de_su_dependencia(pregunta, esperado):
    fila = _unico(_responder(pregunta))[0]
    assert fila["total_productos"] == esperado, (pregunta, fila)


def test_el_caso_reportado_cuenta_los_productos_de_todos_los_materiales_que_se_llaman_desarmador():
    # Con "=" daria 0 (ningun nombre es exactamente "desarmador"); con el JOIN y ILIKE suma los dos materiales.
    r = recetas.buscar("cuantos productos tienen como ID Material \"desarmador\"?")
    sql = json.loads(r)["sql_query"]
    assert "JOIN material" in sql and "ILIKE '%DESARMADOR%'" in sql and "= 'desarmador'" not in sql.lower()
    assert _unico(_responder("cuantos productos tienen como ID Material \"desarmador\"?"))[0]["total_productos"] == 3


def test_la_lista_trae_los_productos_con_el_nombre_del_material():
    filas = _unico(_responder("que productos tienen material desarmador plano"))
    assert sorted(f["producto"] for f in filas) == ["a", "b"]
    assert {f["material"] for f in filas} == {"DESARMADOR PLANO"}


@pytest.mark.parametrize("valor", ["x'; DROP TABLE product; --", "a\" OR 1=1 --", "desarmador%' OR '1'='1"])
def test_el_valor_buscado_no_puede_inyectar_sql(valor):
    r = recetas.buscar(f"cuantos productos tienen material {valor}")
    if r is not None:  # lo que no sea [a-z0-9 ] se descarta antes de llegar al SQL
        sql = json.loads(r)["sql_query"]
        assert "DROP" not in sql.upper() and "OR 1=1" not in sql.upper() and "'1'='1'" not in sql


def test_sin_valor_no_es_una_receta():
    assert recetas.buscar("cuantos productos tienen material") is None


def test_el_esquema_dice_al_modelo_cual_es_la_columna_con_el_nombre_de_cada_dependencia():
    from app.bi.schema_linking import ddl_para_pregunta
    e, aj = _motor(), AjustesBI()
    ddl = ddl_para_pregunta(CacheDeEsquema(e, aj).obtener(), "cuantos productos tienen como id material desarmador")
    assert "id_material int FK>material (nombre: material_description)" in ddl
    assert "id_marca int FK>brand (nombre: brand_description)" in ddl
    assert "id_familia int FK>product_family (nombre: product_family_description)" in ddl


def test_el_glosario_explica_dependencias_y_como_comparar_texto():
    from app.bi.prompt import PLANTILLA
    assert "ID Material" in PLANTILLA and "product.id_material -> material" in PLANTILLA
    assert "ILIKE '%palabra%'" in PLANTILLA and "id_marca" in PLANTILLA and "id_brand" in PLANTILLA
