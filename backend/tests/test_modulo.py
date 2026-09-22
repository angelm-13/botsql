"""Las piezas por separado: extractor, parser de la directiva y ejecutor."""

from __future__ import annotations

import json

import pytest

from bi.directive import DirectivaInvalida, normalizar_tipo, parsear_directiva
from bi.executor import nombres_unicos, valor_json
from bi.schema_extractor import extraer_esquema


# ---------------------------------------------------------------------------
# Extractor de esquema
# ---------------------------------------------------------------------------

def test_se_excluye_la_fontaneria(esquema):
    assert "alembic_version" not in esquema.nombres
    assert "user_mfa" not in esquema.nombres
    assert {"clientes", "productos", "ventas"} <= esquema.nombres


def test_las_columnas_sensibles_no_existen_para_el_modelo(esquema):
    ddl = esquema.a_ddl()
    assert "password_hash" not in ddl
    assert "api_key" not in ddl
    clientes = next(r for r in esquema.relaciones if r.nombre == "clientes")
    assert set(clientes.columnas_omitidas) == {"password_hash", "api_key"}


def test_el_ddl_lleva_llaves_primarias_y_foraneas(esquema):
    ddl = esquema.a_ddl()
    assert "FK -> clientes.id" in ddl
    assert "FK -> productos.id" in ddl
    assert "PK" in ddl


def test_el_ddl_dice_el_motor_y_como_se_acota(esquema):
    ddl = esquema.a_ddl()
    assert "SQLite" in ddl
    assert "LIMIT n" in ddl


def test_una_lista_de_inclusion_manda_sobre_la_de_exclusion(engine, ajustes):
    solo_ventas = extraer_esquema(engine, ajustes.con(incluir=("ventas",)))
    assert {r.nombre for r in solo_ventas.relaciones} == {"ventas"}


def test_la_huella_cambia_si_cambia_lo_expuesto(engine, ajustes, esquema):
    otro = extraer_esquema(engine, ajustes.con(incluir=("ventas",)))
    assert otro.huella != esquema.huella


def test_el_tope_de_tablas_se_respeta_y_se_avisa(engine, ajustes):
    recortado = extraer_esquema(engine, ajustes.con(max_tablas=1))
    assert len(recortado.relaciones) == 1
    assert recortado.truncado
    assert "trunco" in recortado.a_ddl()


# ---------------------------------------------------------------------------
# Parser de la directiva
# ---------------------------------------------------------------------------

DIRECTIVA = {
    "is_dashboard": False,
    "sql_query": "SELECT 1 AS x FROM ventas",
    "explanation": "prueba",
    "visualization": {"chart_type": "bar", "title": "T", "x_axis": "a", "y_axis": "b"},
}


def test_se_acepta_el_json_limpio():
    d = parsear_directiva(json.dumps(DIRECTIVA))
    assert not d.is_dashboard
    assert d.widgets[0].sql_query.startswith("SELECT")


def test_se_quita_la_valla_de_markdown():
    crudo = "```json\n" + json.dumps(DIRECTIVA) + "\n```"
    assert parsear_directiva(crudo).widgets[0].visualization.chart_type == "bar"


def test_se_recorta_la_prosa_alrededor():
    crudo = "Claro, aqui tienes:\n" + json.dumps(DIRECTIVA) + "\nEspero te sirva."
    assert parsear_directiva(crudo).widgets[0].explanation == "prueba"


def test_una_llave_dentro_de_un_literal_no_rompe_el_recorte():
    """El recorte cuenta llaves respetando comillas.

    Buscar de la primera `{` a la ultima `}` fallaria con un SQL que contenga
    una llave dentro de un literal, y ese SQL es perfectamente valido.
    """
    con_llave = dict(DIRECTIVA, sql_query="SELECT '{raro}' AS x FROM ventas")
    crudo = "texto antes " + json.dumps(con_llave) + " texto despues"
    assert "{raro}" in parsear_directiva(crudo).widgets[0].sql_query


def test_se_reconoce_la_negativa_del_modelo():
    d = parsear_directiva('{"error": "Accion no permitida por seguridad"}')
    assert d.rechazada_por_el_modelo
    assert d.widgets == []


def test_un_dashboard_se_recorta_al_tope():
    muchos = {"is_dashboard": True, "widgets": [
        {"sql_query": f"SELECT {i} FROM ventas"} for i in range(30)
    ]}
    d = parsear_directiva(json.dumps(muchos), max_widgets=4)
    assert len(d.widgets) == 4


def test_manda_la_evidencia_y_no_la_etiqueta():
    """`is_dashboard: true` con una sola consulta es una grafica, no un tablero."""
    uno = dict(DIRECTIVA, is_dashboard=True)
    assert not parsear_directiva(json.dumps(uno)).is_dashboard


@pytest.mark.parametrize("bruto,esperado", [
    ("bar", "bar"),
    ("BarChart", "bar"),
    ("grafica_de_barras", "bar"),
    ("gráfico de líneas", "line"),
    ("pastel", "pie"),
    ("donut", "pie"),
    ("tarjeta_kpi", "kpi_card"),
    ("scorecard", "kpi_card"),
    ("", "table"),
    ("algo_que_nadie_dibuja", "table"),
])
def test_el_tipo_se_normaliza(bruto, esperado):
    assert normalizar_tipo(bruto) == esperado


@pytest.mark.parametrize("crudo", ["", "no soy json", "[1,2,3]", '{"sin": "consulta"}'])
def test_una_respuesta_inservible_se_rechaza(crudo):
    with pytest.raises(DirectivaInvalida):
        parsear_directiva(crudo)


# ---------------------------------------------------------------------------
# Ejecutor
# ---------------------------------------------------------------------------

def test_los_tipos_se_vuelven_json():
    import datetime
    import uuid
    from decimal import Decimal

    assert valor_json(Decimal("10.50")) == 10.5
    assert valor_json(datetime.date(2026, 9, 18)) == "2026-09-18"
    assert valor_json(uuid.UUID(int=0)) == "00000000-0000-0000-0000-000000000000"
    assert valor_json(float("nan")) is None          # JSON no tiene NaN
    assert valor_json(float("inf")) is None
    assert valor_json(b"\x01\x02") == "0x0102"


def test_las_columnas_repetidas_no_se_pisan():
    """`SELECT a.id, b.id` devuelve dos columnas `id`.

    Como cada fila es un objeto, sin esto la segunda pisaria a la primera en
    silencio y el usuario veria un dato equivocado sin ninguna senal.
    """
    assert nombres_unicos(["id", "id", "total"]) == ("id", "id_2", "total")


def test_el_tope_de_filas_se_aplica_al_traerlas(cliente, engine, ajustes):
    """No se confia en el LIMIT del texto: se corta al leer.

    Es la unica garantia que funciona igual en un motor sin LIMIT.
    """
    from bi.executor import ejecutar
    from bi.security import validar_sql

    apretado = ajustes.con(limite_filas=7)
    validado = validar_sql("SELECT * FROM ventas", {"ventas"}, motor="sqlite",
                           limite_maximo=1000)     # el texto pide hasta 1000
    resultado = ejecutar(engine, validado, ajustes=apretado)

    assert resultado.total_filas == 7
    assert resultado.truncado


def test_no_se_puede_escribir_ni_saltandose_el_validador(engine, ajustes):
    """La tercera barrera, probada sola.

    Se mete un INSERT directo al ejecutor, saltandose el validador a
    proposito: la transaccion es de solo lectura y la base tiene que
    rechazarlo. Si esta prueba se cae, las otras barreras son lo unico que
    queda.
    """
    from sqlalchemy.exc import SQLAlchemyError

    from bi.executor import ejecutar
    from bi.security import SqlValidado

    falso = SqlValidado(
        sql="INSERT INTO ventas (id, fecha, total) VALUES (99999, '2026-01-01', 1)",
        relaciones=("ventas",), limite=1, se_agrego_limite=False,
    )
    with pytest.raises(SQLAlchemyError):
        ejecutar(engine, falso, ajustes=ajustes)
