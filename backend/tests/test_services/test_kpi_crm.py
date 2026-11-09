"""KPIs de la pestana CRM: clientes, proyectos y tareas.

Corren en SQLite y en PostgreSQL (solo usan SQL portable). "Hoy" sale de `hoy_negocio()`, que aqui se congela con
`tests/reloj.py` para probar tambien que una foto solo se emite el dia de hoy.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime

from app.kpis.modulos import crm
from app.kpis.modulos.crm import (
    clientes_activos_query, clientes_nuevos_query, proyectos_con_entrega_vencida_query, proyectos_por_estado_comercial_query,
    tareas_bloqueadas_por_responsable_query, tareas_por_estado_query,
)
from app.kpis.registry import KPI_POR_CLAVE
from app.kpis.registry import KPI_REGISTRY
from app.models.kpi_definition import KpiDefinition
from app.models.session import transaction_context
from app.routes.kpi import _con_metadatos_del_registry
from tests.kpi_crm_base import CrmBase
from tests.reloj import ahora_local

HOY = date(2026, 10, 28)
AHORA = datetime(2026, 10, 28, 12, 0)


class ClientesNuevosTest(CrmBase):
    def _nuevos(self, inicio, fin):
        with transaction_context() as db:
            return [tuple(f) for f in clientes_nuevos_query(db, inicio, fin, {}, None)]

    def test_cuenta_solo_clientes_vigentes_con_fecha_dentro_del_rango_por_dia(self):
        self._cliente("Inquilino 1", creation_date=datetime(2026, 5, 1, 15, 0))
        self._cliente("Inquilino 2", creation_date=datetime(2026, 5, 1, 16, 0))
        self._cliente("Inquilino 3", creation_date=datetime(2026, 5, 3, 15, 0))
        self._cliente("Inquilino antiguo", creation_date=datetime(2026, 4, 30, 15, 0))     # antes del rango
        self._cliente("Inquilino futuro", creation_date=datetime(2026, 5, 5, 15, 0))       # despues del rango
        self.assertEqual(
            [(None, date(2026, 5, 1), 2), (None, date(2026, 5, 3), 1)],
            self._nuevos(date(2026, 5, 1), date(2026, 5, 4)),
        )

    def test_no_cuenta_proveedores_ni_tipo_nulo_ni_bajas_ni_fecha_nula(self):
        self._cliente("Cliente", creation_date=datetime(2026, 5, 1, 15, 0))
        self._cliente("Proveedor", tipo="supplier", creation_date=datetime(2026, 5, 1, 15, 0))
        self._cliente("Sin tipo", tipo=None, creation_date=datetime(2026, 5, 1, 15, 0))
        self._cliente("Dado de baja", creation_date=datetime(2026, 5, 1, 15, 0), baja=datetime(2026, 5, 2))
        self.assertEqual([(None, date(2026, 5, 1), 1)], self._nuevos(date(2026, 5, 1), date(2026, 5, 1)))

    def test_un_alta_en_la_noche_de_mexico_cuenta_el_dia_del_negocio_no_el_de_utc(self):
        # 20:00 en Mexico del 1 de mayo se guarda como 02:00 UTC del 2: es un cliente del dia 1.
        self._cliente("Inquilino nocturno", creation_date=datetime(2026, 5, 2, 2, 0))
        self.assertEqual([(None, date(2026, 5, 1), 1)], self._nuevos(date(2026, 5, 1), date(2026, 5, 2)))

    def test_un_rango_sin_altas_no_regresa_filas(self):
        self.assertEqual([], self._nuevos(date(2026, 5, 1), date(2026, 5, 31)))

    def test_actor_project_no_acota_el_resultado(self):
        # `alcance_proyecto=False`: recepcion ve todos; un cliente no pertenece a un proyecto.
        self._cliente("Inquilino 1", creation_date=datetime(2026, 5, 1, 15, 0))
        with transaction_context() as db:
            con_proyecto = [tuple(f) for f in clientes_nuevos_query(db, date(2026, 5, 1), date(2026, 5, 1), {}, 999)]
        self.assertEqual([(None, date(2026, 5, 1), 1)], con_proyecto)


class ClientesActivosTest(CrmBase):
    def _activos(self, fecha_fin=HOY, actor_project=None):
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(f) for f in clientes_activos_query(db, fecha_fin, fecha_fin, {}, actor_project)]

    def test_un_cliente_con_un_proyecto_vivo_cuenta_y_se_fecha_hoy(self):
        self._proyecto(self._cliente("Inquilino 1"))
        self.assertEqual([(None, HOY, 1)], self._activos())

    def test_un_cliente_con_varios_proyectos_vivos_cuenta_una_vez(self):
        inquilino = self._cliente("Inquilino 4")
        for _ in range(3):
            self._proyecto(inquilino)
        otro = self._cliente("Inquilino 5")
        self._proyecto(otro)
        self.assertEqual([(None, HOY, 2)], self._activos())

    def test_los_estados_de_taller_que_no_activan_son_completed_denied_y_draft(self):
        for estado in ("completed", "denied", "draft"):
            self._proyecto(self._cliente(f"Cliente {estado}"), estado=estado)
        self.assertEqual([(None, HOY, 0)], self._activos())

    def test_blocked_y_stopped_si_cuentan_como_activos_igual_que_el_resto_del_recorrido(self):
        for estado in ("submitted", "authorized", "blocked", "waiting_material", "in_progress", "stopped", "collected"):
            self._proyecto(self._cliente(f"Cliente {estado}"), estado=estado)
        self.assertEqual([(None, HOY, 7)], self._activos())

    def test_un_proyecto_cancelado_comercialmente_no_activa_pero_un_estado_comercial_nulo_si(self):
        self._proyecto(self._cliente("Cancelado"), comercial="cancelado")
        self._proyecto(self._cliente("Sin estado comercial"), comercial=None)
        self._proyecto(self._cliente("Pendiente"), comercial="pendiente_orden_compra")
        self.assertEqual([(None, HOY, 2)], self._activos())

    def test_si_un_proyecto_sigue_vivo_el_cliente_cuenta_aunque_otro_este_terminado_o_cancelado(self):
        inquilino = self._cliente("Inquilino 7")
        self._proyecto(inquilino, estado="completed")
        self._proyecto(inquilino, comercial="cancelado")
        self._proyecto(inquilino, estado="in_progress")
        self.assertEqual([(None, HOY, 1)], self._activos())

    def test_no_cuenta_proveedores_clientes_de_baja_ni_proyectos_de_baja(self):
        self._proyecto(self._cliente("Proveedor", tipo="supplier"))
        self._proyecto(self._cliente("Cliente sin tipo", tipo=None))
        self._proyecto(self._cliente("Cliente de baja", baja=datetime(2026, 5, 1)))
        self._proyecto(self._cliente("Con proyecto de baja"), baja=datetime(2026, 5, 1))
        self._cliente("Sin proyectos")
        self.assertEqual([(None, HOY, 0)], self._activos())

    def test_actor_project_se_ignora_y_el_conteo_no_se_acota_ni_se_multiplica(self):
        # `alcance_proyecto=False`: el query se calcula una sola vez, sobre todos los proyectos.
        inquilino = self._cliente("Inquilino 4")
        for _ in range(3):
            self._proyecto(inquilino)
        self.assertEqual(self._activos(actor_project=None), self._activos(actor_project=101))
        self.assertEqual([(None, HOY, 1)], self._activos(actor_project=999))

    def test_es_una_foto_de_hoy_un_rango_pasado_no_inventa_filas(self):
        self._proyecto(self._cliente("Inquilino 1"))
        self.assertEqual([], self._activos(fecha_fin=date(2026, 10, 20)))

    def test_sin_clientes_activos_escribe_cero_para_no_dejar_pegado_el_valor_de_ayer(self):
        self.assertEqual([(None, HOY, 0)], self._activos())


class ProyectosPorEstadoComercialTest(CrmBase):
    def _por_estado(self, fecha_fin=HOY, actor_project=None):
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(f) for f in proyectos_por_estado_comercial_query(db, fecha_fin, fecha_fin, {}, actor_project)]

    def test_siempre_regresa_las_cuatro_categorias_en_orden_y_con_cero(self):
        # Solo existe el proyecto interno del admin (id 1), pendiente de orden de compra por omision.
        self.assertEqual([
            ("pendiente_orden_compra", HOY, 1), ("autorizado", HOY, 0), ("cancelado", HOY, 0), ("cobrado", HOY, 0),
        ], self._por_estado())

    def test_cuenta_los_proyectos_vigentes_por_estado_comercial_de_cualquier_cliente_y_estado_de_taller(self):
        inquilino = self._cliente("Inquilino 1")
        proveedor = self._cliente("Proveedor", tipo="supplier")
        self._proyecto(inquilino, estado="draft", comercial="pendiente_orden_compra")
        self._proyecto(inquilino, estado="in_progress", comercial="autorizado")
        self._proyecto(proveedor, estado="completed", comercial="autorizado")
        self._proyecto(inquilino, estado="denied", comercial="cancelado")
        self._proyecto(inquilino, estado="completed", comercial="cobrado")
        self._proyecto(inquilino, comercial="autorizado", baja=datetime(2026, 5, 1))      # de baja: no cuenta
        # (el proyecto interno del admin, id 1, es de un proveedor y esta pendiente de orden de compra por omision)
        self.assertEqual([
            ("pendiente_orden_compra", HOY, 2), ("autorizado", HOY, 2), ("cancelado", HOY, 1), ("cobrado", HOY, 1),
        ], self._por_estado())

    def test_un_estado_comercial_nulo_sale_como_sin_estado_y_solo_cuando_hay(self):
        self._proyecto(self._cliente("Inquilino 1"), comercial=None)
        self.assertEqual(
            ("sin_estado", HOY, 1), self._por_estado()[-1],
            "al final, despues de las cuatro del catalogo",
        )
        self.assertEqual(5, len(self._por_estado()))

    def test_actor_project_se_ignora(self):
        self._proyecto(self._cliente("Inquilino 1"), comercial="autorizado")
        self.assertEqual(self._por_estado(actor_project=None), self._por_estado(actor_project=999))

    def test_es_una_foto_de_hoy_un_rango_pasado_no_inventa_filas(self):
        self._proyecto(self._cliente("Inquilino 1"))
        self.assertEqual([], self._por_estado(fecha_fin=date(2026, 10, 20)))


class ProyectosConEntregaVencidaTest(CrmBase):
    AYER = date(2026, 10, 27)

    def _vencidos(self, fecha_fin=HOY, actor_project=None):
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(f) for f in proyectos_con_entrega_vencida_query(db, fecha_fin, fecha_fin, {}, actor_project)]

    def test_cuenta_solo_los_proyectos_abiertos_cuya_fecha_de_entrega_ya_paso(self):
        inquilino = self._cliente("Inquilino 1")
        self._proyecto(inquilino, entrega=self.AYER)                       # vencido
        self._proyecto(inquilino, entrega=date(2026, 9, 1))                # vencido hace mas
        self._proyecto(inquilino, entrega=HOY)                             # vence hoy: todavia no
        self._proyecto(inquilino, entrega=date(2026, 11, 15))              # en el futuro
        self._proyecto(inquilino, entrega=None)                            # sin fecha: nunca vence
        self.assertEqual([(None, HOY, 2)], self._vencidos())

    def test_no_cuentan_terminados_recolectados_rechazados_ni_cancelados(self):
        inquilino = self._cliente("Inquilino 1")
        for estado in ("completed", "collected", "denied"):
            self._proyecto(inquilino, estado=estado, entrega=self.AYER)
        self._proyecto(inquilino, comercial="cancelado", entrega=self.AYER)
        self.assertEqual([(None, HOY, 0)], self._vencidos())

    def test_bloqueado_y_detenido_cuentan_si_paso_la_fecha(self):
        inquilino = self._cliente("Inquilino 1")
        for estado in ("blocked", "stopped"):
            self._proyecto(inquilino, estado=estado, entrega=self.AYER)
        self.assertEqual([(None, HOY, 2)], self._vencidos())

    def test_un_estado_comercial_nulo_no_es_cancelado_y_un_proyecto_de_baja_no_cuenta(self):
        inquilino = self._cliente("Inquilino 1")
        self._proyecto(inquilino, comercial=None, entrega=self.AYER)
        self._proyecto(inquilino, entrega=self.AYER, baja=datetime(2026, 10, 1))
        self.assertEqual([(None, HOY, 1)], self._vencidos())

    def test_actor_project_se_ignora_y_sin_vencidos_escribe_cero(self):
        self.assertEqual([(None, HOY, 0)], self._vencidos(actor_project=999))

    def test_es_una_foto_de_hoy_un_rango_pasado_no_inventa_filas(self):
        self._proyecto(self._cliente("Inquilino 1"), entrega=date(2026, 9, 1))
        self.assertEqual([], self._vencidos(fecha_fin=date(2026, 10, 20)))


class DefinicionesDeProyectosTest(unittest.TestCase):
    def test_son_de_operaciones_con_grupo_crm_y_sin_alcance_de_proyecto(self):
        for clave in ("proyectos_por_estado_comercial", "proyectos_con_entrega_vencida"):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, f"{clave}: el modulo real no cambia (licencias, permisos, job)")
            self.assertEqual("crm", kpi.grupo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertEqual("ultimo", kpi.agregacion, f"{clave}: es una foto, sumar las noches la multiplicaria")
            self.assertEqual("snapshot", kpi.modo, clave)

    def test_la_dona_de_estado_comercial_es_neutral_con_colores_y_etiquetas_de_cada_categoria(self):
        kpi = KPI_POR_CLAVE["proyectos_por_estado_comercial"]
        self.assertEqual(("estado",), kpi.dimensiones)
        self.assertEqual("dona", kpi.grafica_default)
        self.assertEqual("neutral", kpi.direccion)
        categorias = set(crm.COMERCIAL_CATEGORIAS)
        self.assertEqual(categorias, set(kpi.colores_categoria))
        self.assertEqual(categorias, set(kpi.etiquetas_categoria))
        self.assertEqual(crm.COMERCIAL_CATEGORIAS, kpi.orden_categorias)
        self.assertEqual({"pendiente_orden_compra", "autorizado", "cancelado", "cobrado"}, set(crm.MANAGEMENT_STATUSES))

    def test_las_etiquetas_son_neutrales_sin_terminos_de_coworking(self):
        kpi = KPI_POR_CLAVE["proyectos_por_estado_comercial"]
        textos = " ".join([kpi.etiqueta, kpi.descripcion, *kpi.etiquetas_categoria.values()]).lower()
        for palabra in ("coworking", "inquilino", "oficina", "renta", "espacio", "membres"):
            self.assertNotIn(palabra, textos)

    def test_la_entrega_vencida_es_un_numero_donde_menos_es_mejor(self):
        kpi = KPI_POR_CLAVE["proyectos_con_entrega_vencida"]
        self.assertEqual(("global",), kpi.dimensiones)
        self.assertEqual("bajo_es_mejor", kpi.direccion)
        self.assertEqual("numero", kpi.grafica_default)


class TareasPorEstadoTest(CrmBase):
    def _por_estado(self, fecha_fin=HOY, actor_project=None):
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(f) for f in tareas_por_estado_query(db, fecha_fin, fecha_fin, {}, actor_project)]

    def test_sin_tareas_regresa_las_seis_categorias_del_catalogo_en_cero_y_en_orden(self):
        self.assertEqual(
            [(estado, HOY, 0) for estado in ("pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada")],
            self._por_estado(),
        )

    def test_cuenta_las_tareas_vigentes_de_todos_los_proyectos_por_estado(self):
        ana = self._usuario("Ana (recepcion)")
        oficina_4 = self._proyecto(self._cliente("Inquilino 4"))
        oficina_12 = self._proyecto(self._cliente("Inquilino 12"))
        for proyecto, estado in (
            (oficina_4, "pendiente"), (oficina_4, "pendiente"), (oficina_12, "pendiente"),
            (oficina_4, "en_proceso"), (oficina_12, "bloqueada"), (oficina_12, "en_revision"),
            (oficina_4, "terminada"), (oficina_12, "terminada"), (oficina_4, "cancelada"),
        ):
            self._tarea(ana, proyecto, estado)
        self._tarea(ana, oficina_4, "pendiente", baja=datetime(2026, 5, 1))       # de baja: no cuenta
        self.assertEqual([
            ("pendiente", HOY, 3), ("en_proceso", HOY, 1), ("bloqueada", HOY, 1),
            ("en_revision", HOY, 1), ("terminada", HOY, 2), ("cancelada", HOY, 1),
        ], self._por_estado())

    def test_un_estado_nulo_o_desconocido_sale_como_sin_estado_y_solo_cuando_hay(self):
        ana = self._usuario("Ana")
        oficina = self._proyecto(self._cliente("Inquilino 4"))
        self._tarea(ana, oficina, None)
        self._tarea(ana, oficina, "estatus_viejo")
        self._tarea(ana, oficina, "terminada")
        resultado = self._por_estado()
        self.assertEqual(("sin_estado", HOY, 2), resultado[-1], "al final, despues de las seis del catalogo")
        self.assertEqual(("terminada", HOY, 1), resultado[4])
        self.assertEqual(7, len(resultado))

    def test_actor_project_se_ignora(self):
        self._tarea(self._usuario("Ana"), self._proyecto(self._cliente("Inquilino 4")), "en_proceso")
        self.assertEqual(self._por_estado(actor_project=None), self._por_estado(actor_project=999))

    def test_es_una_foto_de_hoy_un_rango_pasado_no_inventa_filas(self):
        self._tarea(self._usuario("Ana"), self._proyecto(self._cliente("Inquilino 4")))
        self.assertEqual([], self._por_estado(fecha_fin=date(2026, 10, 20)))


class TareasBloqueadasPorResponsableTest(CrmBase):
    def _bloqueadas(self, fecha_fin=HOY, actor_project=None, empleados=None):
        filtros = {"empleados": empleados} if empleados else {}
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(f) for f in tareas_bloqueadas_por_responsable_query(db, fecha_fin, fecha_fin, filtros, actor_project)]

    def test_cuenta_las_bloqueadas_por_responsable_sumando_todos_los_proyectos(self):
        ana, beto = self._usuario("Ana"), self._usuario("Beto")
        oficina_4 = self._proyecto(self._cliente("Inquilino 4"))
        oficina_12 = self._proyecto(self._cliente("Inquilino 12"))
        for proyecto in (oficina_4, oficina_4, oficina_12):
            self._tarea(ana, proyecto, "bloqueada")
        self._tarea(beto, oficina_12, "bloqueada")
        self._tarea(beto, oficina_12, "en_proceso")                               # no bloqueada
        self._tarea(ana, oficina_4, "bloqueada", baja=datetime(2026, 5, 1))       # de baja: no cuenta
        self.assertEqual([(ana, HOY, 3), (beto, HOY, 1)], self._bloqueadas())

    def test_un_responsable_sin_bloqueadas_sale_en_cero_para_que_el_valor_de_ayer_no_se_quede_pegado(self):
        ana, beto = self._usuario("Ana"), self._usuario("Beto")
        oficina = self._proyecto(self._cliente("Inquilino 4"))
        self._tarea(ana, oficina, "terminada")
        self._tarea(beto, oficina, "bloqueada")
        self.assertEqual([(ana, HOY, 0), (beto, HOY, 1)], self._bloqueadas())

    def test_sin_ninguna_tarea_escribe_una_fila_sin_responsable_en_cero(self):
        self.assertEqual([(None, HOY, 0)], self._bloqueadas())

    def test_filtra_por_empleados_cuando_la_api_lo_pide(self):
        ana, beto = self._usuario("Ana"), self._usuario("Beto")
        oficina = self._proyecto(self._cliente("Inquilino 4"))
        self._tarea(ana, oficina, "bloqueada")
        self._tarea(beto, oficina, "bloqueada")
        self.assertEqual([(beto, HOY, 1)], self._bloqueadas(empleados=[beto]))

    def test_actor_project_se_ignora(self):
        self._tarea(self._usuario("Ana"), self._proyecto(self._cliente("Inquilino 4")), "bloqueada")
        self.assertEqual(self._bloqueadas(actor_project=None), self._bloqueadas(actor_project=999))

    def test_es_una_foto_de_hoy_un_rango_pasado_no_inventa_filas(self):
        self._tarea(self._usuario("Ana"), self._proyecto(self._cliente("Inquilino 4")), "bloqueada")
        self.assertEqual([], self._bloqueadas(fecha_fin=date(2026, 10, 20)))


class DefinicionesDeTareasTest(unittest.TestCase):
    def test_son_de_operaciones_con_grupo_crm_y_sin_alcance_de_proyecto(self):
        for clave in ("tareas_por_estado", "tareas_bloqueadas_por_responsable"):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, f"{clave}: el modulo real no cambia (licencias, permisos, job)")
            self.assertEqual("crm", kpi.grupo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertEqual("ultimo", kpi.agregacion, f"{clave}: es una foto, sumar las noches la multiplicaria")
            self.assertEqual("snapshot", kpi.modo, clave)

    def test_la_dona_de_tareas_es_neutral_y_cubre_cada_estado_del_catalogo(self):
        kpi = KPI_POR_CLAVE["tareas_por_estado"]
        self.assertEqual(("estado",), kpi.dimensiones)
        self.assertEqual("dona", kpi.grafica_default)
        self.assertEqual("neutral", kpi.direccion)
        categorias = {*crm.TASK_STATUSES, "sin_estado"}
        self.assertEqual(categorias, set(kpi.colores_categoria))
        self.assertEqual(categorias, set(kpi.etiquetas_categoria))
        self.assertEqual(crm.TAREAS_CATEGORIAS, kpi.orden_categorias)
        self.assertEqual("Sin estado", kpi.etiquetas_categoria["sin_estado"])

    def test_las_bloqueadas_por_responsable_son_barras_donde_menos_es_mejor_y_ocultan_los_ceros(self):
        kpi = KPI_POR_CLAVE["tareas_bloqueadas_por_responsable"]
        self.assertEqual(("empleado",), kpi.dimensiones)
        self.assertEqual(("barras",), kpi.graficas_permitidas)
        self.assertEqual("bajo_es_mejor", kpi.direccion)
        self.assertTrue(kpi.ocultar_ceros)
        self.assertEqual("Responsable", kpi.etiqueta_dimension)


SEIS_DE_CRM = {
    "clientes_nuevos": "crm", "clientes_activos": "crm",
    "proyectos_por_estado_comercial": "operaciones", "proyectos_con_entrega_vencida": "operaciones",
    "tareas_por_estado": "operaciones", "tareas_bloqueadas_por_responsable": "operaciones",
}


class PestanaCrmTest(unittest.TestCase):
    def test_los_seis_salen_en_la_pestana_crm_y_cada_uno_conserva_su_modulo_real(self):
        con_grupo_crm = {kpi.clave: kpi.modulo for kpi in KPI_REGISTRY if kpi.grupo == "crm"}
        self.assertEqual(SEIS_DE_CRM, con_grupo_crm)

    def test_ninguno_de_los_seis_tiene_alcance_de_proyecto_y_todos_son_de_serie_de_snapshots(self):
        for clave in SEIS_DE_CRM:
            kpi = KPI_POR_CLAVE[clave]
            self.assertFalse(kpi.alcance_proyecto, f"{clave}: en un coworking cada inquilino es un proyecto y recepcion los ve todos")
            self.assertEqual("snapshot", kpi.modo, clave)

    def test_la_api_entrega_el_grupo_junto_al_modulo_real(self):
        for numero, (clave, modulo) in enumerate(SEIS_DE_CRM.items(), start=900):
            fila = KpiDefinition(clave=clave, etiqueta=clave, modulo=modulo, dimensiones=["global"], unidad="numero")
            fila.id_kpi_definition = numero
            resultado = _con_metadatos_del_registry(fila)
            self.assertEqual("crm", resultado["grupo"], clave)
            self.assertEqual(modulo, resultado["modulo"], f"{clave}: licencias y permisos siguen leyendo el modulo")

    def test_las_direcciones_pedidas(self):
        self.assertEqual("alto_es_mejor", KPI_POR_CLAVE["clientes_nuevos"].direccion)
        for clave in ("proyectos_por_estado_comercial", "tareas_por_estado"):
            self.assertEqual("neutral", KPI_POR_CLAVE[clave].direccion, clave)
        for clave in ("proyectos_con_entrega_vencida", "tareas_bloqueadas_por_responsable"):
            self.assertEqual("bajo_es_mejor", KPI_POR_CLAVE[clave].direccion, clave)


class DefinicionesDeClientesTest(unittest.TestCase):
    def test_los_dos_son_del_modulo_crm_con_grupo_crm_y_sin_alcance_de_proyecto(self):
        for clave in ("clientes_nuevos", "clientes_activos"):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("crm", kpi.modulo, clave)
            self.assertEqual("crm", kpi.grupo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertEqual(("global",), kpi.dimensiones, clave)
            self.assertEqual("snapshot", kpi.modo, clave)

    def test_clientes_nuevos_es_un_flujo_que_se_suma_y_sube_es_mejor(self):
        kpi = KPI_POR_CLAVE["clientes_nuevos"]
        self.assertEqual("suma", kpi.agregacion)
        self.assertEqual("alto_es_mejor", kpi.direccion)
        self.assertEqual("barras", kpi.grafica_default)
        self.assertIs(kpi.query_builder, crm.clientes_nuevos_query)

    def test_clientes_activos_es_una_foto_numero(self):
        kpi = KPI_POR_CLAVE["clientes_activos"]
        self.assertEqual("ultimo", kpi.agregacion, "sumar las noches multiplicaria los clientes por los dias del rango")
        self.assertEqual("numero", kpi.grafica_default)
        self.assertIs(kpi.query_builder, crm.clientes_activos_query)


if __name__ == "__main__":
    unittest.main()
