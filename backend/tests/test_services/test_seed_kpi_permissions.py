from __future__ import annotations

import contextlib
import io
from datetime import datetime

from sqlalchemy import select

from app.kpis.modulos import checadas
from app.models.entity_permission import EntityPermission
from app.models.kpi_definition import KpiDefinition
from app.models.nm_permission_kpi import NmPermissionKpi
from app.models.permission import Permission
from app.models.session import transaction_context
from scripts.seed_kpi_permissions import ASIGNACIONES, AsignacionRol, main, validar
from tests.conftest import BackendTestCase

ADMINISTRATOR = 1
ALMACENISTA = 6


class TestValidacionDeAsignaciones(BackendTestCase):
    def test_la_asignacion_de_adser_es_valida(self):
        self.assertEqual([], validar(ASIGNACIONES["adser"]))

    def test_adser_deja_fuera_kpis_sin_datos_reales_para_su_almacen(self):
        # articulos_bajo_stock: almacen de herramientas individuales, casi
        # toda la existencia es 1 -- "bajo stock" no aplica.
        # vales_vencidos_por_responsable: depende de nm_incident_product.
        # due_date, vacio en el 100% de lo migrado de Adser.
        # material_prestado_actual SI se incluye: usa Incident.incident_date
        # como fecha de prestamo, no due_date/start_date -- ese si esta
        # poblado real.
        claves = {clave for asignacion in ASIGNACIONES["adser"] for clave in asignacion.kpis}
        self.assertEqual(
            {
                "incidentes_resueltos_por_empleado",
                "incidencias_abiertas_por_empleado",
                "incidencias_pendientes",
                "incidencias_abiertas_vs_cerradas",
                "material_por_estado",
                "material_prestado_actual",
            },
            claves,
        )

    def test_rol_acotado_no_recibe_un_kpi_sin_alcance_de_proyecto(self):
        errores = validar((AsignacionRol("Admin Restaurante", acotado_a_proyecto=True,
                                         kpis=("articulos_bajo_stock", "ventas_por_empleado")),))
        self.assertEqual(1, len(errores))
        self.assertIn("articulos_bajo_stock", errores[0])
        self.assertIn("acotado a proyecto", errores[0])

    def test_la_asignacion_de_comala_es_valida(self):
        self.assertEqual([], validar(ASIGNACIONES["comala"]))

    def test_comala_da_a_adm_asistencias_los_siete_kpis_de_checadas_y_ninguno_mas(self):
        (asignacion,) = ASIGNACIONES["comala"]
        self.assertEqual("adm_asistencias", asignacion.rol)
        self.assertFalse(asignacion.acotado_a_proyecto, "una checada no tiene proyecto")
        self.assertEqual(7, len(asignacion.kpis))
        # La lista se compara con el modulo, no con una copia: un KPI de checadas nuevo que no se asigne aqui hace fallar esta prueba.
        self.assertEqual({kpi.clave for kpi in checadas.definiciones()}, set(asignacion.kpis))
        self.assertIn("checadas_con_duracion_anomala", asignacion.kpis)

    def test_comala_no_hereda_nada_de_adser(self):
        de_adser = {clave for asignacion in ASIGNACIONES["adser"] for clave in asignacion.kpis}
        de_comala = {clave for asignacion in ASIGNACIONES["comala"] for clave in asignacion.kpis}
        self.assertEqual(set(), de_adser & de_comala)
        self.assertEqual({"adser", "comala"}, set(ASIGNACIONES))

    def test_un_rol_acotado_a_proyecto_no_podria_recibir_los_kpis_de_checadas(self):
        # Por eso adm_asistencias va con acotado_a_proyecto=False: los siete son alcance_proyecto=False.
        (asignacion,) = ASIGNACIONES["comala"]
        errores = validar((AsignacionRol(asignacion.rol, acotado_a_proyecto=True, kpis=asignacion.kpis),))
        self.assertEqual(7, len(errores))
        self.assertTrue(all("acotado a proyecto" in error for error in errores))

    def test_clave_inexistente_es_error(self):
        errores = validar((AsignacionRol("Administrator", False, ("no_existe",)),))
        self.assertEqual(1, len(errores))
        self.assertIn("no existe en KPI_REGISTRY", errores[0])


class TestSiembraDePermisosDeKpi(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                Permission(id_permission=ADMINISTRATOR, permission_description="Administrator", created_by=1,
                           authorized_by=1, id_department=1, id_subdepartment=1, id_level=1),
                Permission(id_permission=ALMACENISTA, permission_description="Almacenista", created_by=1,
                           authorized_by=1, id_department=1, id_subdepartment=1, id_level=1),
                # Capa 1 de Administrator, como la siembra ROLES.
                EntityPermission(id_permission=ADMINISTRATOR, entity_name="kpi_definition", scope_create=4,
                                 scope_read=4, scope_update=4, scope_delete=4, created_by=1),
            ])
            for clave in (
                "incidentes_resueltos_por_empleado",
                "incidencias_abiertas_por_empleado",
                "incidencias_pendientes",
                "incidencias_abiertas_vs_cerradas",
                "material_por_estado",
                "material_prestado_actual",
            ):
                db.add(KpiDefinition(clave=clave, etiqueta=clave, modulo="inventario", dimensiones=["producto"]))

    def _correr(self, *argv):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = main(list(argv))
        return codigo, salida.getvalue()

    def _vistos(self, id_permission=ADMINISTRATOR):
        with transaction_context() as db:
            return sorted(db.scalars(
                select(KpiDefinition.clave)
                .join(NmPermissionKpi, NmPermissionKpi.id_kpi_definition == KpiDefinition.id_kpi_definition)
                .where(NmPermissionKpi.id_permission == id_permission, NmPermissionKpi.deletion_date.is_(None),
                       NmPermissionKpi.puede_ver.is_(True))
            ).all())

    ADSER_KPIS = [
        "incidencias_abiertas_por_empleado",
        "incidencias_abiertas_vs_cerradas",
        "incidencias_pendientes",
        "incidentes_resueltos_por_empleado",
        "material_por_estado",
        "material_prestado_actual",
    ]

    def test_dry_run_no_escribe_nada(self):
        codigo, salida = self._correr("--perfil", "adser", "--dry-run")

        self.assertEqual(0, codigo)
        self.assertIn("Se insertarian: 6", salida)
        self.assertEqual([], self._vistos())

    def test_siembra_los_seis_kpis_y_es_idempotente(self):
        codigo, salida = self._correr("--perfil", "adser")
        self.assertEqual(0, codigo)
        self.assertIn("Insertadas: 6", salida)
        self.assertEqual(self.ADSER_KPIS, self._vistos())
        self.assertEqual([], self._vistos(ALMACENISTA))

        codigo, salida = self._correr("--perfil", "adser")
        self.assertEqual(0, codigo)
        self.assertIn("Insertadas: 0", salida)
        with transaction_context() as db:
            self.assertEqual(6, len(db.scalars(select(NmPermissionKpi)).all()))

    def test_no_reactiva_un_permiso_dado_de_baja(self):
        with transaction_context() as db:
            id_kpi = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "material_por_estado"))
            db.add(NmPermissionKpi(id_permission=ADMINISTRATOR, id_kpi_definition=id_kpi, puede_ver=True,
                                   created_by=1, deletion_date=datetime(2026, 9, 1)))

        codigo, salida = self._correr("--perfil", "adser")

        self.assertEqual(0, codigo)
        self.assertIn("NO se reactiva", salida)
        self.assertEqual([clave for clave in self.ADSER_KPIS if clave != "material_por_estado"], self._vistos())

    def test_un_borrado_fisico_desde_la_pantalla_se_reasigna_al_volver_a_correr(self):
        # /kpi_permissions borra la fila (BaseService.delete), no la da de
        # baja: para el script es igual a "nunca asignado". Documentado en el
        # docstring y en docs/despliegues; esta prueba fija el comportamiento.
        self._correr("--perfil", "adser")
        with transaction_context() as db:
            fila = db.scalar(
                select(NmPermissionKpi)
                .join(KpiDefinition, KpiDefinition.id_kpi_definition == NmPermissionKpi.id_kpi_definition)
                .where(KpiDefinition.clave == "material_por_estado")
            )
            db.delete(fila)

        codigo, salida = self._correr("--perfil", "adser")

        self.assertEqual(0, codigo)
        self.assertIn("Insertadas: 1", salida)
        self.assertEqual(self.ADSER_KPIS, self._vistos())

    def test_rol_inexistente_se_reporta_y_no_se_crea(self):
        with transaction_context() as db:
            db.get(Permission, ADMINISTRATOR).deletion_date = datetime(2026, 9, 1)

        codigo, salida = self._correr("--perfil", "adser")

        self.assertEqual(2, codigo)
        self.assertIn("ROL INEXISTENTE: 'Administrator'", salida)
        with transaction_context() as db:
            self.assertEqual(0, len(db.scalars(select(NmPermissionKpi)).all()))
            self.assertEqual(2, len(db.scalars(select(Permission)).all()), "no crea roles")

    def test_avisa_si_al_rol_le_falta_la_capa_de_modulo(self):
        with transaction_context() as db:
            fila = db.scalar(select(EntityPermission).where(EntityPermission.entity_name == "kpi_definition"))
            fila.scope_read = 0

        codigo, salida = self._correr("--perfil", "adser", "--dry-run")

        self.assertEqual(0, codigo)
        self.assertIn("no tiene lectura de kpi_definition", salida)


ADM_ASISTENCIAS = 7


class TestDryRunDelPerfilComala(BackendTestCase):
    """`--perfil comala --dry-run` sobre la base de la prueba: lista lo que haria y no escribe nada."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                Permission(id_permission=ADM_ASISTENCIAS, permission_description="adm_asistencias", created_by=1,
                           authorized_by=1, id_department=1, id_subdepartment=1, id_level=1),
                EntityPermission(id_permission=ADM_ASISTENCIAS, entity_name="kpi_definition", scope_create=0,
                                 scope_read=4, scope_update=0, scope_delete=0, created_by=1),
            ])
            for clave in ASIGNACIONES["comala"][0].kpis:
                db.add(KpiDefinition(clave=clave, etiqueta=clave, modulo="operaciones", dimensiones=["empleado"]))

    def _correr(self, *argv):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = main(list(argv))
        return codigo, salida.getvalue()

    def test_dry_run_de_comala_lista_los_siete_y_no_escribe_nada(self):
        codigo, salida = self._correr("--perfil", "comala", "--dry-run")

        self.assertEqual(0, codigo)
        self.assertIn("dry-run: no se escribe nada", salida)
        self.assertIn("Se insertarian: 7", salida)
        for clave in ASIGNACIONES["comala"][0].kpis:
            self.assertRegex(salida, rf"adm_asistencias\s+{clave}\s+INSERTAR")
        self.assertNotIn("ROL INEXISTENTE", salida)
        self.assertNotIn("AVISO", salida, "el rol ya tiene la capa 1: sin avisos")
        with transaction_context() as db:
            self.assertEqual(0, len(db.scalars(select(NmPermissionKpi)).all()), "el dry-run no escribe")

    def test_dry_run_de_comala_avisa_si_el_rol_no_existe_y_no_lo_crea(self):
        with transaction_context() as db:
            db.get(Permission, ADM_ASISTENCIAS).deletion_date = datetime(2026, 10, 1)

        codigo, salida = self._correr("--perfil", "comala", "--dry-run")

        self.assertEqual(2, codigo)
        self.assertIn("ROL INEXISTENTE: 'adm_asistencias'", salida)
        with transaction_context() as db:
            self.assertEqual(0, len(db.scalars(select(NmPermissionKpi)).all()))
            self.assertEqual(1, len(db.scalars(select(Permission)).all()), "no crea roles")

    def test_dry_run_de_comala_avisa_si_al_rol_le_falta_la_capa_de_modulo(self):
        with transaction_context() as db:
            db.scalar(select(EntityPermission).where(EntityPermission.entity_name == "kpi_definition")).scope_read = 0

        codigo, salida = self._correr("--perfil", "comala", "--dry-run")

        self.assertEqual(0, codigo)
        self.assertIn("no tiene lectura de kpi_definition", salida)
