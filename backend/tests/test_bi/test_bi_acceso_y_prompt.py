"""Pruebas puras del modulo BI: top N, seleccion de tablas, SQL oculto."""

from app.bi.prompt import detectar_top_n
from app.bi.schema_extractor import Columna, EsquemaDB, Relacion
from app.bi.schema_linking import relaciones_para_pregunta
from app.bi.service import WidgetResuelto
from app.bi.acceso import Acceso


def _esquema(n=40):
    rels = [Relacion(nombre=f"tabla_{i}", columnas=(Columna("id", "INTEGER", es_pk=True),)) for i in range(n)]
    rels += [
        Relacion(nombre="invoice", columnas=(Columna("id_invoice", "INTEGER", es_pk=True),
                                             Columna("total", "NUMERIC"))),
        Relacion(nombre="incident", columnas=(Columna("id_incident", "INTEGER", es_pk=True),)),
    ]
    return EsquemaDB(motor="postgresql", motor_legible="PostgreSQL", version="16",
                     relaciones=tuple(rels), total_encontradas=len(rels))


def test_top_n_se_lee_de_la_pregunta():
    assert detectar_top_n("Top 8 productos por existencias") == 8
    assert detectar_top_n("dame los 12 mejores clientes") == 12
    assert detectar_top_n("cuantas facturas hay") is None


def test_la_tabla_relevante_entra_al_prompt():
    elegidas, resto = relaciones_para_pregunta(_esquema(), "total de facturas del mes")
    assert "invoice" in [r.nombre for r in elegidas]
    assert resto, "las demas tablas quedan solo como indice"


def test_el_sql_no_sale_en_la_respuesta_salvo_que_se_pida():
    w = WidgetResuelto(ok=True, sql="SELECT 1", explanation="x", visualization={})
    assert "sql" not in w.a_dict()
    w.exponer_sql = True
    assert w.a_dict()["sql"] == "SELECT 1"


def test_acceso_limita_tablas():
    a = Acceso("rol-9", False, frozenset({"invoice"}), frozenset({"total"}))
    assert a.permite_tabla("INVOICE") and not a.permite_tabla("user")
    assert Acceso("admin", True, None).permite_tabla("cualquiera")
