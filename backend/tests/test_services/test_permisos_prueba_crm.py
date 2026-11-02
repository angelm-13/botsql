"""El script de permisos del rol de prueba local: da `puede_ver` a los seis KPIs de CRM y a nada mas, y avisa lo que falta en la capa 1."""

from __future__ import annotations

import contextlib
import io

from sqlalchemy import func, select

from app.kpis.registry import KPI_POR_CLAVE
from app.models import Department, EntityPermission, KpiDefinition, Level, NmPermissionKpi, Permission, Subdepartment
from app.models.session import transaction_context
from scripts import permisos_prueba_crm as script
from tests.conftest import BackendTestCase

ROL = "PRUEBA sin permisos"
OTRO_KPI = "ventas_por_empleado"


class PermisosPruebaCrmTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            for id_permission, nombre in ((20, ROL), (21, "Otro rol")):
                db.add(Permission(
                    id_permission=id_permission, permission_description=nombre, created_by=1, authorized_by=1,
                    id_department=1, id_subdepartment=1, id_level=1,
                ))
            for clave in (*script.SEIS_KPIS_DE_CRM, OTRO_KPI):
                kpi = KPI_POR_CLAVE[clave]
                db.add(KpiDefinition(clave=clave, etiqueta=kpi.etiqueta, modulo=kpi.modulo, dimensiones=list(kpi.dimensiones),
                                     unidad=kpi.unidad, created_by=1))

    def _correr(self, funcion, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = funcion(*argumentos)
        return codigo, salida.getvalue()

    def _claves_del_rol(self, id_permission=20):
        with transaction_context() as db:
            return sorted(db.scalars(
                select(KpiDefinition.clave).join(NmPermissionKpi, NmPermissionKpi.id_kpi_definition == KpiDefinition.id_kpi_definition)
                .where(NmPermissionKpi.id_permission == id_permission, NmPermissionKpi.puede_ver.is_(True))
            ))

    def test_dry_run_por_omision_no_escribe(self):
        codigo, salida = self._correr(script.conceder, ROL, False)
        self.assertEqual(0, codigo)
        self.assertEqual([], self._claves_del_rol())
        self.assertIn("Se insertarian: 6", salida)
        self.assertIn("DRY-RUN", salida)

    def test_aplicar_da_solo_los_seis_kpis_de_crm_al_rol_pedido_y_es_idempotente(self):
        self._correr(script.conceder, ROL, True)
        self.assertEqual(sorted(script.SEIS_KPIS_DE_CRM), self._claves_del_rol())
        self.assertEqual([], self._claves_del_rol(21), "otro rol no recibe nada")
        self._correr(script.conceder, ROL, True)
        with transaction_context() as db:
            self.assertEqual(6, db.scalar(select(func.count()).select_from(NmPermissionKpi)), "correr dos veces no duplica")

    def test_un_rol_que_no_existe_se_reporta_y_no_se_crea(self):
        codigo, salida = self._correr(script.conceder, "Rol inexistente", True)
        self.assertEqual(2, codigo)
        self.assertIn("ROL INEXISTENTE", salida)
        with transaction_context() as db:
            self.assertEqual(0, db.scalar(select(func.count()).select_from(NmPermissionKpi)))
            self.assertIsNone(db.scalar(select(Permission.id_permission).where(Permission.permission_description == "Rol inexistente")))

    def test_avisa_lo_que_falta_en_la_capa_1_sin_escribir_entity_permission(self):
        _, salida = self._correr(script.conceder, ROL, True)
        self.assertIn("lectura de `kpi_definition`", salida)
        self.assertIn("lectura de `kpi_dashboard`", salida)
        with transaction_context() as db:
            self.assertEqual(0, db.scalar(select(func.count()).select_from(EntityPermission)), "la capa 1 la maneja el Gestor")

    def test_avisa_si_la_lectura_no_es_todos_porque_cinco_de_los_seis_darian_403(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=20, entity_name="kpi_definition", scope_read=1, created_by=1))
            db.add(EntityPermission(id_permission=20, entity_name="kpi_dashboard", scope_read=4, created_by=1))
        _, salida = self._correr(script.conceder, ROL, False)
        self.assertIn("no es Todos", salida)
        self.assertNotIn("le falta la lectura", salida)

    def test_sin_avisos_cuando_la_capa_1_esta_completa(self):
        with transaction_context() as db:
            for entidad in ("kpi_definition", "kpi_dashboard"):
                db.add(EntityPermission(id_permission=20, entity_name=entidad, scope_read=4, created_by=1))
        _, salida = self._correr(script.conceder, ROL, False)
        self.assertNotIn("AVISO", salida)

    def test_deshacer_retira_solo_esas_seis_filas_del_rol(self):
        with transaction_context() as db:
            ids = {clave: i for i, clave in db.execute(select(KpiDefinition.id_kpi_definition, KpiDefinition.clave)).all()}
            db.add(NmPermissionKpi(id_permission=20, id_kpi_definition=ids[OTRO_KPI], puede_ver=True, created_by=1))
        self._correr(script.conceder, ROL, True)
        self._correr(script.conceder, "Otro rol", True)
        codigo, salida = self._correr(script.retirar, ROL, False)
        self.assertIn("Se retirarian 6", salida)
        self.assertEqual(7, len(self._claves_del_rol()), "el dry-run no borra")
        self._correr(script.retirar, ROL, True)
        self.assertEqual([OTRO_KPI], self._claves_del_rol(), "queda el KPI que no es de CRM")
        self.assertEqual(sorted(script.SEIS_KPIS_DE_CRM), self._claves_del_rol(21), "el otro rol conserva los suyos")

    def test_los_seis_son_los_de_la_pestana_crm(self):
        self.assertEqual(set(script.SEIS_KPIS_DE_CRM), {k for k, definicion in KPI_POR_CLAVE.items() if definicion.grupo == "crm"})
