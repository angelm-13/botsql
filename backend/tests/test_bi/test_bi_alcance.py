"""Alcance Propios / Mis grupos / Todos del gestor de roles aplicado al SQL del BI."""

import pytest

from app.bi.acceso import Acceso, acotar_sql
from app.bi.schema_extractor import Columna, EsquemaDB, Relacion
from app.bi.security import SqlRechazado

ESQ = EsquemaDB(motor="postgresql", motor_legible="PostgreSQL", version="16", total_encontradas=2, relaciones=(
    Relacion(nombre="invoice", esquema="public", columnas=(Columna("id_invoice", "INTEGER"), Columna("created_by", "INTEGER"))),
    Relacion(nombre="brand", esquema="public", columnas=(Columna("id_brand", "INTEGER"),)),
))


def acc(leer, uid=7):
    return Acceso("r", False, None, permisos=(("invoice", 4, leer, 4, 4),), user_id=uid)


def test_propios_filtra_por_created_by():
    sql = acotar_sql("SELECT count(*) FROM invoice", acc(1), ESQ)
    assert sql.startswith('WITH "invoice" AS (SELECT * FROM "public"."invoice" WHERE (created_by = 7))')


def test_mis_grupos_usa_los_equipos():
    sql = acotar_sql("SELECT * FROM invoice", acc(2), ESQ)
    assert "nm_team_user" in sql and "UNION SELECT 7" in sql


def test_todos_y_admin_no_cambian_el_sql():
    q = "SELECT * FROM invoice"
    assert acotar_sql(q, acc(4), ESQ) == q
    assert acotar_sql(q, Acceso("a", True, None), ESQ) == q


def test_tabla_limitada_sin_dueno_se_niega_y_con_todos_pasa():
    for leer in (1, 2):
        a = Acceso("r", False, None, permisos=(("brand", 4, leer, 4, 4),), user_id=7)
        with pytest.raises(SqlRechazado):
            acotar_sql("SELECT * FROM brand", a, ESQ)
    a = Acceso("r", False, None, permisos=(("brand", 4, 4, 4, 4),), user_id=7)
    assert acotar_sql("SELECT * FROM brand", a, ESQ) == "SELECT * FROM brand"


def test_se_une_a_un_with_existente():
    sql = acotar_sql("WITH x AS (SELECT 1) SELECT * FROM invoice", acc(1), ESQ)
    assert sql.startswith('WITH "invoice" AS') and ", x AS (SELECT 1) SELECT" in sql


@pytest.mark.parametrize("q", ["SELECT * FROM public.invoice", "WITH RECURSIVE r AS (SELECT 1) SELECT * FROM invoice"])
def test_no_se_deja_saltar_el_filtro(q):
    with pytest.raises(SqlRechazado):
        acotar_sql(q, acc(1), ESQ)


def test_sin_usuario_falla_cerrado():
    with pytest.raises(SqlRechazado):
        acotar_sql("SELECT * FROM invoice", acc(1, uid=None), ESQ)


def test_auditor_llm_registra_sin_bloquear(caplog, monkeypatch):
    import json, logging
    from app.bi import auditor

    class Falso:
        def generar(self, prompt, pregunta="", formato=None):
            from types import SimpleNamespace
            assert "created_by" in prompt and "Id de usuario: 7" in prompt
            return SimpleNamespace(texto=json.dumps({"estado": "FALLIDO", "riesgos": "x"}))

    monkeypatch.setenv("BI_AUDITOR_LLM", "1")
    with caplog.at_level(logging.INFO, logger="bi.audit"):
        auditor._auditar(Falso(), "ventas de todos", acc(1), {"id_user": 7}, ["WITH x AS (created_by) SELECT 1"])
    assert "FALLIDO" in caplog.text
    # administrador o apagado: no hace nada
    monkeypatch.setenv("BI_AUDITOR_LLM", "0")
    assert auditor.auditar_en_segundo_plano(None, "p", acc(1), {}, ["s"]) is None


def test_proyecto_tambien_es_del_lider():
    esq = EsquemaDB(motor="postgresql", motor_legible="PostgreSQL", version="16", total_encontradas=1, relaciones=(
        Relacion(nombre="proyect", esquema="public", columnas=(Columna("created_by", "INTEGER"), Columna("leader", "INTEGER"))),))
    a = Acceso("r", False, None, permisos=(("proyect", 4, 1, 4, 4),), user_id=7)
    assert "(created_by = 7 OR leader = 7)" in acotar_sql("SELECT * FROM proyect", a, esq)


def test_un_cte_con_nombre_de_tabla_restringida_no_tapa_el_filtro():
    with pytest.raises(SqlRechazado):
        acotar_sql("WITH invoice AS (SELECT * FROM invoice) SELECT count(*) FROM invoice", acc(1), ESQ)
    # con Todos no hay filtro que tapar
    q = "WITH invoice AS (SELECT * FROM invoice) SELECT count(*) FROM invoice"
    assert acotar_sql(q, acc(4), ESQ) == q
