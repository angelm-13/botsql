"""Busqueda global, pronostico y reparacion de consultas: funciones puras."""

from app.bi import busqueda, prediccion
from app.bi.schema_extractor import Columna, EsquemaDB, Relacion
from app.bi.service import _reparar_sql


def _esquema():
    r = Relacion(nombre="product", columnas=(
        Columna("id_product", "INTEGER", es_pk=True), Columna("descripcion", "VARCHAR(200)"),
        Columna("product_code", "VARCHAR(30)"), Columna("cantidad", "INTEGER"),
        Columna("deletion_date", "TIMESTAMP")))
    return EsquemaDB(motor="postgresql", motor_legible="PostgreSQL", version="16",
                     relaciones=(r,), total_encontradas=1)


def test_detecta_el_termino_de_busqueda():
    assert busqueda.detectar("busca ACE133") == "ace133"
    assert busqueda.detectar("¿Dónde aparece Roberto Cisneros?") == "roberto cisneros"
    assert busqueda.detectar("cuantos productos hay") is None


def test_la_busqueda_solo_recorre_columnas_de_texto_del_esquema_y_no_inyecta():
    sqls = busqueda.sentencias(_esquema(), "ace'; DROP TABLE x;--")
    texto = " ".join(sqls)
    assert "descripcion" in texto and "product_code" in texto
    assert "cantidad" not in texto
    assert "'" not in texto.split("ILIKE")[1].split("%")[1] and ";" not in texto


def test_pronostico_de_una_tendencia_lineal_exacta():
    r = prediccion.pronosticar([10, 20, 30, 40], 2)
    assert round(r["pasos"][0][0]) == 50 and round(r["pasos"][1][0]) == 60
    assert r["r2"] > 0.99


def test_sin_historia_suficiente_no_pronostica():
    filas, texto, _ = prediccion.construir_tabla([{"mes": "2026-01", "valor": 1}, {"mes": "2026-02", "valor": 2}], 3, "vales")
    assert filas is None and "al menos 3 meses" in texto


def test_la_tabla_marca_historico_y_pronostico_y_avisa_si_hay_poca_historia():
    hist = [{"mes": f"2026-0{i}", "valor": i * 2} for i in range(1, 5)]
    filas, _, avisos = prediccion.construir_tabla(hist, 2, "vales")
    assert [f["tipo"] for f in filas] == ["historico"] * 4 + ["pronostico"] * 2
    assert filas[-1]["mes"] == "2026-06"
    assert any("poco confiable" in a for a in avisos)


def test_detecta_peticiones_de_prediccion():
    assert prediccion.es_prediccion("predice los vales de los proximos 3 meses")
    assert prediccion.horizonte("pronostico de los proximos 6 meses") == 6
    assert not prediccion.es_prediccion("cuantos vales hay")


def test_repara_una_columna_inventada_con_las_reales():
    e = _esquema()
    assert _reparar_sql("SELECT p.product_name FROM product p",
                        "column p.product_name does not exist", e) == "SELECT p.descripcion FROM product p"
    assert _reparar_sql("SELECT zzz FROM product", 'column "zzz" does not exist', e) is None
