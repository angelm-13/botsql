"""La documentacion que recibe cada rol depende de lo que su rol puede leer."""

from app.bi import conocimiento as c
from app.bi.acceso import Acceso


def _titulos(acceso):
    c.invalidar()
    return {f.fuente for f in c.fragmentos(acceso) if f.fuente.endswith(".md")}


def test_un_rol_sin_facturas_no_recibe_el_manual_de_facturacion():
    taller = Acceso("rol-t", False, frozenset({"product", "location", "proyect", "incident"}))
    fuentes = _titulos(taller)
    assert "facturacion.md" not in fuentes
    assert "inventario.md" in fuentes and "operaciones.md" in fuentes


def test_el_administrador_recibe_todos_los_manuales():
    fuentes = _titulos(Acceso("admin", True, None))
    assert {"facturacion.md", "rh.md", "seguridad.md", "inventario.md"} <= fuentes


def test_sin_rol_solo_recibe_lo_general():
    fuentes = _titulos(Acceso("sin-rol", False, frozenset()))
    assert "facturacion.md" not in fuentes and "rh.md" not in fuentes
    assert "sistema_general.md" in fuentes


def test_la_documentacion_tecnica_es_solo_de_administradores(monkeypatch, tmp_path):
    (tmp_path / "infra.md").write_text("# Despliegue\nProcedimiento interno de despliegue en k3s para el equipo.\n", encoding="utf-8")
    monkeypatch.setenv("BI_KB_ADMIN_DIRS", str(tmp_path))
    assert "infra.md" not in _titulos(Acceso("rol-x", False, frozenset({"product"})))
    assert "infra.md" in _titulos(Acceso("admin", True, None))


def test_mis_permisos_refleja_el_gestor():
    a = Acceso("rol-p", False, frozenset({"product"}), rol="Almacenista",
               permisos=(("product", 0, 4, 4, 0),))
    c.invalidar()
    textos = " ".join(f.texto for f in c.fragmentos(a) if f.titulo.startswith("Mis permisos"))
    assert "Almacenista" in textos and "editar (todo)" in textos and "eliminar" not in textos
