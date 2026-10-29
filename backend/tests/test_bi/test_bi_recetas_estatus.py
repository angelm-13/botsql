"""Recetas que arreglan lo que un modelo chico adivina mal: el valor guardado de un estatus."""

import pytest

from app.bi import recetas


@pytest.mark.parametrize("pregunta, trozo", [
    ("cuantos proyectos estan entregados", "proyect_status = 'delivered'"),
    ("cuantas tareas estan pendientes", "task_status = 'pendiente'"),
    ("cuantos vales estan en borrador", "incident_status = 'borrador'"),
    ("cuantas incidencias estan cerradas", "incident_status = 'cerrada'"),
    ("productos por marca", "id_marca"),
    ("cuantos usuarios son empleados", "is_employee = true"),
    ("cuantas incidencias se registraron este mes", "date_trunc('month', now())"),
])
def test_la_receta_usa_el_valor_real(pregunta, trozo):
    assert trozo in (recetas.buscar(pregunta) or "")


def test_un_estatus_desconocido_va_al_modelo():
    assert recetas.buscar("cuantos proyectos estan volando") is None


def test_vales_de_un_tipo_usa_el_catalogo_y_por_responsable_no_recorta():
    assert "ILIKE '%prestamo%material%'" in recetas.buscar("cuantos vales son de prestamo de material")
    assert "LIMIT" not in recetas.buscar("incidencias por responsable")
    assert "LIMIT 5" in recetas.buscar("top 5 empleados con mas incidencias")


def test_vales_de_cada_tipo_no_se_toma_como_un_tipo_llamado_cada():
    assert recetas.buscar("cuantos vales hay de cada tipo") is None
    assert recetas.buscar("cuantos vales hay por tipo") is None
