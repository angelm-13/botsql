"""La barrera de seguridad: lo que debe caer y lo que NO debe caer.

Las dos mitades importan por igual. Un validador que rechaza todo es seguro y
tambien inutil: cada falso positivo es una pregunta legitima que el usuario ve
fallar sin entender por que, y la reaccion no es reformular -- es dejar de usar
la herramienta.
"""

from __future__ import annotations

import pytest

from bi.security import (
    SqlRechazado,
    advertencias_de_despliegue,
    forzar_limite,
    relaciones_referenciadas,
    validar_sql,
)

OCULTAS = ("password*", "*api_key*", "secret")


def validar(sql: str, esquema, motor: str = "sqlite"):
    return validar_sql(sql, esquema.nombres, motor=motor,
                       limite_maximo=100, columnas_ocultas=OCULTAS)


# ---------------------------------------------------------------------------
# Lo que tiene que caer
# ---------------------------------------------------------------------------

ATAQUES = [
    ("enunciado encadenado", "SELECT 1 FROM ventas; DROP TABLE ventas", "varios_enunciados"),
    ("escritura directa", "DELETE FROM ventas", "no_es_lectura"),
    ("actualizacion directa", "UPDATE ventas SET total = 0", "no_es_lectura"),
    ("cte que escribe", "WITH x AS (DELETE FROM ventas RETURNING *) SELECT * FROM x",
     "palabra_prohibida"),
    ("select into", "SELECT * FROM ventas INTO copia", "palabra_prohibida"),
    ("tabla filtrada por politica", "SELECT * FROM user_mfa", "relacion_no_permitida"),
    ("tabla inexistente", "SELECT * FROM nomina", "relacion_no_permitida"),
    ("catalogo del sistema", "SELECT name FROM sqlite_master", "catalogo_del_sistema"),
    ("columna sensible por nombre", "SELECT nombre, password_hash FROM clientes",
     "columna_sensible"),
    ("union hacia lo filtrado", "SELECT id FROM ventas UNION SELECT id FROM user_mfa",
     "relacion_no_permitida"),
    ("attach de otra base", "SELECT * FROM ventas WHERE 1=1 ATTACH DATABASE 'x' AS y",
     "palabra_prohibida"),
    ("consulta sin origen", "SELECT 1", "sin_origen"),
    ("vacio", "   ", "sql_vacio"),
]


@pytest.mark.parametrize("etiqueta,sql,motivo", ATAQUES, ids=[a[0] for a in ATAQUES])
def test_lo_peligroso_no_llega_a_la_base(etiqueta, sql, motivo, esquema):
    with pytest.raises(SqlRechazado) as exc:
        validar(sql, esquema)
    assert exc.value.motivo == motivo


@pytest.mark.parametrize("motor,sql", [
    ("postgresql", "SELECT pg_read_file('/etc/passwd') FROM ventas"),
    ("postgresql", "SELECT * FROM ventas WHERE pg_sleep(30)"),
    ("mysql", "SELECT load_file('/etc/passwd') FROM ventas"),
    ("mssql", "SELECT * FROM ventas WHERE 1=1 EXEC xp_cmdshell 'dir'"),
    ("sqlite", "SELECT load_extension('x') FROM ventas"),
])
def test_las_funciones_peligrosas_de_cada_motor(motor, sql, esquema):
    """Lo que es inofensivo en un motor es una fuga en otro.

    `load_file` no existe en PostgreSQL y `pg_read_file` no existe en MySQL:
    por eso la lista es por motor y no una sola lista global, que seria a la
    vez mas larga y mas laxa.
    """
    with pytest.raises(SqlRechazado):
        validar(sql, esquema, motor=motor)


# ---------------------------------------------------------------------------
# Lo que NO debe caer
# ---------------------------------------------------------------------------

LEGITIMAS = [
    ("literal que dice update", "SELECT * FROM ventas WHERE 'update' = 'update'"),
    ("literal que dice drop", "SELECT * FROM clientes WHERE nombre = 'drop table'"),
    ("funcion replace", "SELECT REPLACE(nombre, 'a', 'b') AS n FROM clientes"),
    ("cte de lectura", "WITH t AS (SELECT id_cliente, SUM(total) s FROM ventas "
                       "GROUP BY id_cliente) SELECT * FROM t ORDER BY s DESC"),
    ("join de tres tablas", "SELECT c.nombre, p.nombre, v.total FROM ventas v "
                            "JOIN clientes c ON c.id = v.id_cliente "
                            "JOIN productos p ON p.id = v.id_producto"),
    ("subconsulta", "SELECT * FROM ventas WHERE id_cliente IN (SELECT id FROM clientes)"),
    ("comentario al final", "SELECT total FROM ventas -- solo las ventas\n"),
    ("punto y coma final", "SELECT total FROM ventas;"),
]


@pytest.mark.parametrize("etiqueta,sql", LEGITIMAS, ids=[l[0] for l in LEGITIMAS])
def test_lo_legitimo_pasa(etiqueta, sql, esquema):
    validado = validar(sql, esquema)
    assert validado.sql
    assert "LIMIT" in validado.sql.upper()


def test_el_literal_sobrevive_a_la_validacion(esquema):
    """El SQL que se ejecuta conserva sus literales.

    Se valida sobre un "esqueleto" con los literales vaciados -- para que
    `WHERE nota = 'update'` no cuente como un UPDATE -- pero lo que se ejecuta
    es el SQL de verdad. Confundir los dos convierte `WHERE ciudad = 'CDMX'`
    en `WHERE ciudad = ''`: cero filas, sin ningun error, sin ninguna pista.
    """
    validado = validar("SELECT * FROM clientes WHERE ciudad = 'CDMX'", esquema)
    assert "'CDMX'" in validado.sql


def test_el_comentario_no_llega_al_sql_ejecutable(esquema):
    """Un comentario final se tragaria el LIMIT que se agrega despues."""
    validado = validar("SELECT total FROM ventas -- ; DROP TABLE ventas\n", esquema)
    assert "DROP" not in validado.sql.upper()
    assert validado.sql.rstrip().upper().endswith("LIMIT 100")


# ---------------------------------------------------------------------------
# El tope de filas
# ---------------------------------------------------------------------------

def test_se_agrega_el_limite_si_no_viene(esquema):
    validado = validar("SELECT * FROM ventas", esquema)
    assert validado.se_agrego_limite
    assert validado.limite == 100


def test_se_respeta_un_limite_mas_chico(esquema):
    validado = validar("SELECT * FROM ventas LIMIT 5", esquema)
    assert validado.limite == 5
    assert not validado.se_agrego_limite


def test_se_recorta_un_limite_mas_grande(esquema):
    validado = validar("SELECT * FROM ventas LIMIT 99999", esquema)
    assert validado.limite == 100
    assert "LIMIT 100" in validado.sql


def test_en_sql_server_no_se_toca_el_texto():
    """T-SQL no tiene LIMIT: inyectarlo romperia la consulta.

    Ahi el tope lo impone el ejecutor al traer las filas, que es la garantia
    que funciona en todos los motores.
    """
    sql, limite, agregado = forzar_limite("SELECT TOP (10) * FROM ventas", 100, "mssql")
    assert "LIMIT" not in sql.upper()
    assert not agregado
    assert limite == 100


# ---------------------------------------------------------------------------
# Deteccion de relaciones
# ---------------------------------------------------------------------------

def test_un_cte_no_cuenta_como_tabla():
    relaciones = relaciones_referenciadas(
        "WITH reciente AS (SELECT * FROM ventas) SELECT * FROM reciente"
    )
    assert relaciones == ("ventas",)


def test_se_detectan_las_tablas_de_todos_los_join():
    relaciones = relaciones_referenciadas(
        "SELECT * FROM ventas v JOIN clientes c ON c.id = v.id_cliente "
        "LEFT JOIN productos p ON p.id = v.id_producto"
    )
    assert set(relaciones) == {"ventas", "clientes", "productos"}


def test_se_reclama_un_usuario_privilegiado():
    avisos = advertencias_de_despliegue("postgresql://postgres:x@host/erp")
    assert any("superusuario" in a for a in avisos)

    assert not any(
        "superusuario" in a
        for a in advertencias_de_despliegue("postgresql://bi_lector:x@host/erp")
    )
