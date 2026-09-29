"""Plantilla de tablero de KPIs de Adser (scripts/seed_kpi_dashboard_template.py).

Dos cosas distintas:
* Las cuentas de fechas son las MISMAS que hace el Dashboard en
  frontend/src/kpi/kpiRango.js: los valores esperados de aqui son los de
  frontend/src/kpi/kpi.test.js para el mismo dia (29-sep-2026).
* La siembra, contra la base de pruebas: dry-run, idempotencia, respeto a lo que
  alguien ya cambio, y que sin permisos o sin usuario no escriba nada.
"""

from __future__ import annotations

import contextlib
import io
from datetime import date

from sqlalchemy import select

from app.models.kpi_dashboard import KpiDashboard
from app.models.kpi_dashboard_widget import KpiDashboardWidget
from app.models.kpi_dashboard_widget_kpi import KpiDashboardWidgetKpi
from app.models.kpi_definition import KpiDefinition
from app.models.nm_permission_kpi import NmPermissionKpi
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.user import User
from scripts.seed_kpi_dashboard_template import (
    NOMBRE_TABLERO, PLANTILLA, WidgetPlantilla, main, parametros_del_widget,
    periodo_anterior, resolver_rango_relativo, validar,
)
from tests.conftest import BackendTestCase

HOY = date(2026, 9, 29)
ADMINISTRATOR = 1
TAROJ = 500


class TestFechasRelativas(BackendTestCase):
    def test_cada_rango_da_lo_mismo_que_el_dashboard(self):
        esperado = {
            "hoy": ("2026-09-29", "2026-09-29"),
            "7_dias": ("2026-09-23", "2026-09-29"),
            "30_dias": ("2026-08-31", "2026-09-29"),
            "90_dias": ("2026-07-02", "2026-09-29"),
            "este_mes": ("2026-09-01", "2026-09-29"),
            "mes_anterior": ("2026-08-01", "2026-08-31"),
            "este_anio": ("2026-01-01", "2026-09-29"),
        }
        for clave, (inicio, fin) in esperado.items():
            self.assertEqual((inicio, fin), tuple(f.isoformat() for f in resolver_rango_relativo(clave, HOY)), clave)

    def test_mes_anterior_en_los_bordes(self):
        self.assertEqual((date(2025, 12, 1), date(2025, 12, 31)), resolver_rango_relativo("mes_anterior", date(2026, 1, 15)))
        self.assertEqual((date(2026, 2, 1), date(2026, 2, 28)), resolver_rango_relativo("mes_anterior", date(2026, 3, 1)))
        self.assertEqual((date(2028, 2, 1), date(2028, 2, 29)), resolver_rango_relativo("mes_anterior", date(2028, 3, 5)))

    def test_periodo_anterior_misma_duracion(self):
        self.assertEqual((date(2026, 8, 3), date(2026, 8, 31)), periodo_anterior(date(2026, 9, 1), date(2026, 9, 29)))
        self.assertEqual((date(2026, 7, 1), date(2026, 7, 31)), periodo_anterior(date(2026, 8, 1), date(2026, 8, 31)))

    def test_los_parametros_son_los_que_guarda_el_editor(self):
        self.assertEqual(
            {"rango_relativo": "este_mes", "fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-29",
             "comparar_anterior": True, "fecha_inicio_b": "2026-08-03", "fecha_fin_b": "2026-08-31"},
            parametros_del_widget(WidgetPlantilla("x", "barras", "este_mes", comparar_anterior=True), HOY),
        )
        # "Hoy contra hace 30 dias": un dia contra otro dia, no contra ayer.
        self.assertEqual(
            {"rango_relativo": "hoy", "fecha_inicio": "2026-09-29", "fecha_fin": "2026-09-29",
             "comparar_desfase_dias": 30, "fecha_inicio_b": "2026-08-30", "fecha_fin_b": "2026-08-30"},
            parametros_del_widget(WidgetPlantilla("x", "numero", "hoy", comparar_desfase_dias=30), HOY),
        )
        self.assertEqual(
            {"rango_relativo": "30_dias", "fecha_inicio": "2026-08-31", "fecha_fin": "2026-09-29"},
            parametros_del_widget(WidgetPlantilla("x", "barras", "30_dias"), HOY),
        )
        # Una tabla de un KPI en vivo no guarda periodo; solo su ancho, y solo si es doble.
        self.assertEqual({}, parametros_del_widget(WidgetPlantilla("material_prestado_actual", "tabla"), HOY))
        self.assertEqual({"columnas": 2}, parametros_del_widget(WidgetPlantilla("material_prestado_actual", "tabla", columnas=2), HOY))
        self.assertEqual({"filas": 2}, parametros_del_widget(WidgetPlantilla("material_prestado_actual", "tabla", filas=2), HOY))
        self.assertEqual({"columnas": 2, "filas": 2}, parametros_del_widget(next(w for w in PLANTILLA if w.tipo_grafica == "tabla"), HOY))
        # Solo una tabla guarda tamano.
        self.assertEqual({"rango_relativo": "hoy", "fecha_inicio": "2026-09-29", "fecha_fin": "2026-09-29"},
                         parametros_del_widget(WidgetPlantilla("x", "barras", "hoy", columnas=2, filas=2), HOY))


class TestPlantillaEnSi(BackendTestCase):
    def test_son_los_cinco_widgets_acordados(self):
        self.assertEqual(
            [
                ("material_prestado_actual", "tabla", "", 0),
                ("incidencias_pendientes", "numero", "hoy", 30),
                ("incidencias_abiertas_vs_cerradas", "barras", "este_anio", 0),
                ("incidencias_abiertas_por_empleado", "barras", "este_anio", 0),
                ("material_por_estado", "dona", "hoy", 0),
            ],
            [(w.clave_kpi, w.tipo_grafica, w.rango_relativo, w.comparar_desfase_dias) for w in PLANTILLA],
        )
        # incidentes_resueltos_por_empleado ya no va en la plantilla.
        self.assertNotIn("incidentes_resueltos_por_empleado", [w.clave_kpi for w in PLANTILLA])

    def test_es_valida(self):
        self.assertEqual([], validar())

    def test_un_kpi_en_vivo_no_lleva_rango_y_uno_de_serie_si(self):
        self.assertEqual([], validar((WidgetPlantilla("material_prestado_actual", "tabla"),)))
        self.assertEqual(1, len(validar((WidgetPlantilla("material_prestado_actual", "tabla", "30_dias"),))))
        self.assertGreaterEqual(len(validar((WidgetPlantilla("material_prestado_actual", "tabla", comparar_desfase_dias=30),))), 1)
        self.assertEqual(1, len(validar((WidgetPlantilla("incidencias_pendientes", "numero"),))), "serie sin rango")

    def test_detecta_grafica_no_admitida_kpi_inexistente_y_rango_desconocido(self):
        errores = validar((
            WidgetPlantilla("incidencias_pendientes", "dona", "7_dias"),
            WidgetPlantilla("no_existe", "barras", "7_dias"),
            WidgetPlantilla("material_por_estado", "dona", "trimestre"),
            WidgetPlantilla("material_por_estado", "dona", "hoy", comparar_anterior=True, comparar_desfase_dias=30),
        ))
        self.assertEqual(4, len(errores), errores)


class TestSiembraDelTablero(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(Permission(id_permission=ADMINISTRATOR, permission_description="Administrator", created_by=1,
                              authorized_by=1, id_department=1, id_subdepartment=1, id_level=1))
            db.add(User(id_user=TAROJ, created_by=1, full_name="taroj", id_permission=ADMINISTRATOR, id_proyect=1,
                        id_status=1, supervisor=1, user_type="admin", username="taroj"))
            db.flush()
            for w in PLANTILLA:
                db.add(KpiDefinition(clave=w.clave_kpi, etiqueta=w.clave_kpi, modulo="operaciones", dimensiones=["empleado"]))

    def _dar_permiso(self):
        with transaction_context() as db:
            for id_kpi in db.scalars(select(KpiDefinition.id_kpi_definition)).all():
                db.add(NmPermissionKpi(id_permission=ADMINISTRATOR, id_kpi_definition=id_kpi, puede_ver=True, created_by=1))

    def _correr(self, *argv):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = main(list(argv), hoy=HOY)
        return codigo, salida.getvalue()

    def _tableros(self):
        with transaction_context() as db:
            return db.scalars(select(KpiDashboard).where(KpiDashboard.deletion_date.is_(None))).all()

    def _widgets(self):
        with transaction_context() as db:
            filas = db.execute(
                select(KpiDashboardWidget, KpiDefinition.clave)
                .join(KpiDashboardWidgetKpi, KpiDashboardWidgetKpi.id_kpi_dashboard_widget == KpiDashboardWidget.id_kpi_dashboard_widget)
                .join(KpiDefinition, KpiDefinition.id_kpi_definition == KpiDashboardWidgetKpi.id_kpi_definition)
                .where(KpiDashboardWidget.deletion_date.is_(None))
                .order_by(KpiDashboardWidget.posicion_orden)
            ).all()
            return [(w.tipo_grafica, clave, w.parametros, w.posicion_orden) for w, clave in filas]

    def test_dry_run_no_escribe_nada(self):
        self._dar_permiso()
        codigo, salida = self._correr("--dry-run")
        self.assertEqual(0, codigo)
        self.assertIn("Se crearian: 1 tablero(s) y 5 widget(s)", salida)
        self.assertEqual([], self._tableros())
        self.assertEqual([], self._widgets())

    def test_la_tabla_avisa_que_no_se_corra_en_adser_prod_sin_confirmar_incident_date(self):
        self._dar_permiso()
        _, salida = self._correr("--dry-run")
        self.assertIn("AVISO", salida)
        self.assertIn("incident_date", salida)
        self.assertIn("adser-prod", salida)
        self.assertIn("--sin-tabla", salida)

    def test_sin_tabla_crea_los_otros_cuatro_y_no_avisa(self):
        self._dar_permiso()
        codigo, salida = self._correr("--sin-tabla")
        self.assertEqual(0, codigo, salida)
        self.assertNotIn("AVISO", salida)
        self.assertEqual(
            ["incidencias_pendientes", "incidencias_abiertas_vs_cerradas", "incidencias_abiertas_por_empleado", "material_por_estado"],
            [clave for _, clave, _, _ in self._widgets()],
        )

    def test_crea_el_tablero_y_los_cinco_widgets_como_los_crea_el_editor(self):
        self._dar_permiso()
        codigo, salida = self._correr()
        self.assertEqual(0, codigo, salida)
        tableros = self._tableros()
        self.assertEqual([(TAROJ, NOMBRE_TABLERO)], [(t.id_user, t.nombre) for t in tableros])
        widgets = self._widgets()
        self.assertEqual(
            [(w.tipo_grafica, w.clave_kpi) for w in PLANTILLA],
            [(tipo, clave) for tipo, clave, _, _ in widgets],
        )
        self.assertEqual([100, 200, 300, 400, 500], [orden for *_, orden in widgets])
        por_clave = {clave: parametros for _, clave, parametros, _ in widgets}
        # Los parametros son exactamente los del editor: la instruccion relativa + la foto de hoy.
        self.assertEqual(
            {"rango_relativo": "hoy", "fecha_inicio": "2026-09-29", "fecha_fin": "2026-09-29",
             "comparar_desfase_dias": 30, "fecha_inicio_b": "2026-08-30", "fecha_fin_b": "2026-08-30"},
            por_clave["incidencias_pendientes"],
        )
        # "Este anio", no 30 o 90 dias: en Adser el ultimo vale migrado es del 15 de
        # agosto y no hay capturas nuevas, asi que un rango corto sale vacio.
        for clave in ("incidencias_abiertas_vs_cerradas", "incidencias_abiertas_por_empleado"):
            self.assertEqual("este_anio", por_clave[clave]["rango_relativo"], clave)
            self.assertEqual("2026-01-01", por_clave[clave]["fecha_inicio"], clave)
            self.assertEqual("2026-09-29", por_clave[clave]["fecha_fin"], clave)
        self.assertEqual({"columnas": 2, "filas": 2}, por_clave["material_prestado_actual"], "el KPI en vivo no lleva rango, solo su tamano 2x2")
        self.assertEqual("hoy", por_clave["material_por_estado"]["rango_relativo"])
        self.assertNotIn("comparar_anterior", por_clave["material_por_estado"])

    def test_es_idempotente_y_respeta_lo_que_alguien_cambio(self):
        self._dar_permiso()
        self.assertEqual(0, self._correr()[0])
        # Alguien cambia el rango de un widget.
        with transaction_context() as db:
            widget = db.scalars(select(KpiDashboardWidget).order_by(KpiDashboardWidget.posicion_orden)).first()
            widget.parametros = {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}
        codigo, salida = self._correr()
        self.assertEqual(0, codigo)
        self.assertIn("Creados: 0 tablero(s) y 0 widget(s)", salida)
        self.assertEqual(1, len(self._tableros()))
        widgets = self._widgets()
        self.assertEqual(5, len(widgets))
        self.assertEqual({"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}, widgets[0][2], "no se pisa lo cambiado")

    def test_completa_un_tablero_al_que_le_falta_un_widget(self):
        self._dar_permiso()
        self._correr()
        with transaction_context() as db:
            ultimo = db.scalars(select(KpiDashboardWidget).order_by(KpiDashboardWidget.posicion_orden.desc())).first()
            ultimo.deletion_date = __import__("datetime").datetime(2026, 9, 29)
        codigo, salida = self._correr()
        self.assertEqual(0, codigo)
        self.assertIn("Creados: 0 tablero(s) y 1 widget(s)", salida)
        self.assertEqual(5, len(self._widgets()))
        self.assertEqual(1, len(self._tableros()))

    def test_sin_permiso_sobre_los_kpis_no_escribe_nada(self):
        codigo, salida = self._correr()
        self.assertEqual(1, codigo)
        self.assertIn("seed_kpi_permissions", salida)
        self.assertEqual([], self._tableros())
        self.assertEqual([], self._widgets())

    def test_usuario_inexistente_sale_con_2_y_no_escribe(self):
        self._dar_permiso()
        codigo, salida = self._correr("--usuario", "nadie")
        self.assertEqual(2, codigo)
        self.assertIn("'nadie' no existe", salida)
        self.assertEqual([], self._tableros())
