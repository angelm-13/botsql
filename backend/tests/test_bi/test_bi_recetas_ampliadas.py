"""Recetas ampliadas: formas naturales de preguntar lo mismo se resuelven sin el modelo, con el
resultado correcto, y lo ambiguo NO se contesta en silencio."""

import json

import pytest
from sqlalchemy import create_engine, text

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
    with e.begin() as c:
        for ddl in (
            "CREATE TABLE product (id_product INTEGER PRIMARY KEY, product_code TEXT, descripcion TEXT, cantidad INTEGER, id_marca INTEGER, deletion_date TEXT)",
            "CREATE TABLE material (id_material INTEGER PRIMARY KEY, id_brand INTEGER, deletion_date TEXT)",
            "CREATE TABLE brand (id_brand INTEGER PRIMARY KEY, brand_description TEXT)",
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
        c.execute(text("INSERT INTO material (id_brand, deletion_date) VALUES (1, NULL), (1, NULL), (2, NULL), (2, '2026-01-01')"))
        c.execute(text("INSERT INTO brand VALUES (1, 'Marca1'), (2, 'Marca2')"))
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
    "proyectos activos", "valor del inventario", "total facturado", "facturado este mes", "usuarios activos",
    "proyectos por cliente", "facturas pendientes de pago", "herramientas prestadas",
])
def test_lo_ambiguo_sigue_yendo_al_modelo(pregunta):
    assert recetas.buscar(pregunta) is None


def test_ninguna_receta_nueva_usa_limit_sin_que_se_pida_un_top():
    # Regla del prompt: LIMIT solo con "top N" (un LIMIT de mas trunca agrupaciones).
    for p in ("cuántos vales hay por estatus", "tareas por estatus", "facturas por estatus", "materiales por marca",
              "productos agotados", "cuántos usuarios hay"):
        assert "LIMIT" not in json.loads(recetas.buscar(p))["sql_query"].upper(), p
