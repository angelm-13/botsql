"""Banco de ejemplos verificados: formato, recuperacion y respeto de permisos."""

import json

from app.bi import ejemplos as E
from app.bi.acceso import Acceso


def test_el_banco_tiene_ejemplos_validos():
    banco = E._leer(E.BANCO)
    assert len(banco) > 100
    for e in banco[:200]:
        assert e["sql"].upper().startswith("SELECT") and e["preguntas"] and e["tablas"]
        assert ";" not in e["sql"]


def test_recupera_ejemplos_parecidos_a_la_pregunta():
    r = E.buscar("cuantos usuarios hay registrados")
    assert r and "user" in r[0]["tablas"]


def test_un_rol_sin_la_tabla_no_recibe_ejemplos_que_la_usen():
    sin_user = Acceso("rol-x", False, frozenset({"product"}))
    for e in E.buscar("cuantos usuarios hay registrados", sin_user):
        assert all(sin_user.permite_tabla(t) for t in e["tablas"])


def test_formatea_el_bloque_para_el_prompt():
    bloque = E.formatear(E.buscar("productos por marca"), "productos por marca")
    assert bloque.startswith("EJEMPLOS REALES") and "SELECT" in bloque


def test_aprende_una_consulta_buena_una_sola_vez(tmp_path, monkeypatch):
    ruta = tmp_path / "aprendido.jsonl"
    monkeypatch.setattr(E, "RUTA_APRENDIDO", str(ruta))
    E.aprender("cuantos vales hay", "SELECT COUNT(*) FROM incident", ["incident"], 1)
    E.aprender("cuantos vales hay", "SELECT COUNT(*) FROM incident", ["incident"], 1)
    E.aprender("nada", "SELECT 1", [], 0)       # sin filas: no se guarda
    lineas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()]
    assert len(lineas) == 1 and lineas[0]["origen"] == "aprendido"


def test_el_limit_de_un_ejemplo_sin_top_n_no_se_copia_al_prompt():
    from app.bi import ejemplos
    e = [{"preguntas": ["materiales por marca"], "sql": "SELECT 1 FROM x GROUP BY 1 LIMIT 200"},
         {"preguntas": ["top 5 productos"], "sql": "SELECT 1 FROM y LIMIT 5"}]
    out = ejemplos.formatear(e, "materiales por marca")
    assert "GROUP BY 1\n" in out and "LIMIT 200" not in out and "LIMIT 5" in out
