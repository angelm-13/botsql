"""Catalogo de KPIs predefinidos: el usuario los parametriza, no los crea.

Por que existe
--------------
Un KPI no es una fila que alguien arma desde cero: que se mide y como se
calcula es codigo, declarado aqui en `KPI_REGISTRY`. Lo unico que un usuario
elige por KPI es su parametrizacion -- rango de fechas, que empleados, que
tipo de grafica-- que se guarda aparte, en `kpi_dashboard_widget.parametros`.

`KpiDefinition` en este archivo es el descriptor en codigo de un indicador
(clave, etiqueta, que query lo calcula). No confundir con el modelo
SQLAlchemy homonimo `app.models.kpi_definition.KpiDefinition`, que es la fila
de catalogo en la base -- una por cada entrada de `KPI_REGISTRY`, sembrada por
`seed_kpi_definitions()` en cada arranque.

Como se valida
---------------
Igual que `app/modules/registry.py`: `_validar()` revienta al importar si dos
KPIs comparten clave o si alguno declara un modulo que no existe en
`MODULOS` (`app/modules/registry.py`).
"""

from __future__ import annotations

import json

from sqlalchemy import func, or_, select, text

from app.models.invoice import Invoice
from app.modules.registry import MODULO_POR_CLAVE


def ventas_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ventas facturadas por empleado (`Invoice.created_by`) y por dia.

    Decisiones tomadas contra el codigo real, no supuestas -- ver el reporte
    de la tarea para el detalle de donde se confirmo cada una:

    * Campo de venta: `subtotal`, no `total`. `total` ya trae el IVA sumado
      (`quotation_service.calculate_totals`, `invoice_builder.py`: el total
      es la base gravable mas impuestos menos retenciones), que es dinero que
      se entrega a la autoridad fiscal, no ingreso de la empresa. `subtotal`
      es la suma de los importes de los conceptos antes de impuesto: la venta
      real.
    * Vigencia: se excluyen `invoice_status = 'cotizacion'` (todavia no es una
      venta, es una cotizacion sin convertir -- ver
      `routes/invoice.convert_quotation_invoice`) y
      `invoice_status = 'cancelada'` (mismo criterio que usa
      `invoice_credit_note_service`, que filtra exactamente
      `Invoice.invoice_status != 'cancelada'`). Todo lo demas que deja el
      ciclo de vida (`pendiente`, `parcial`, `pagada`, `timbrada`) es una
      venta vigente.
    * Direccion: `invoice_direction` solo lo puebla la clasificacion de XML
      importado (`invoice_xml_classification.classify_invoice_direction`,
      valores `venta`/`compra`/`sin_clasificar`); una factura de venta
      capturada a mano -el camino normal de CRM, ver `manual_invoice_service`-
      se queda con `invoice_direction` en NULL. Por eso el filtro excluye
      unicamente `'compra'` en vez de exigir `'venta'`: exigirlo dejaria fuera
      casi todas las facturas de venta normales.
    """
    fecha_col = func.date(Invoice.date_emision)
    condiciones = [
        Invoice.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
        Invoice.invoice_status.notin_(["cotizacion", "cancelada"]),
        or_(Invoice.invoice_direction.is_(None), Invoice.invoice_direction != "compra"),
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Invoice.created_by.in_(empleados))
    if actor_project is not None:
        condiciones.append(Invoice.id_proyect == actor_project)

    stmt = (
        select(Invoice.created_by, fecha_col.label("fecha"), func.sum(Invoice.subtotal))
        .where(*condiciones)
        .group_by(Invoice.created_by, fecha_col)
        .order_by(Invoice.created_by, fecha_col)
    )
    return session.execute(stmt).all()


class KpiDefinition:
    def __init__(self, clave, etiqueta, modulo, dimensiones,
                 query_builder, unidad="numero"):
        self.clave = clave
        self.etiqueta = etiqueta
        self.modulo = modulo               # clave de MODULOS en app/modules/registry.py
        self.dimensiones = dimensiones      # tupla, ej. ("empleado",)
        self.query_builder = query_builder  # ver firma de ventas_por_empleado_query
        self.unidad = unidad


KPI_REGISTRY = (
    KpiDefinition(
        clave="ventas_por_empleado",
        etiqueta="Ventas por empleado",
        modulo="facturacion",
        dimensiones=("empleado",),
        query_builder=ventas_por_empleado_query,
        unidad="moneda",
    ),
)


def _validar():
    claves = [kpi.clave for kpi in KPI_REGISTRY]
    if len(claves) != len(set(claves)):
        raise RuntimeError("Hay dos KPIs con la misma clave.")
    for kpi in KPI_REGISTRY:
        if kpi.modulo not in MODULO_POR_CLAVE:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' apunta al modulo inexistente '{kpi.modulo}'."
            )


_validar()


def seed_kpi_definitions(engine) -> None:
    """Siembra `kpi_definition` desde `KPI_REGISTRY`.

    Se corre en cada arranque (ver `init_db.py`), igual que el resto de los
    catalogos: la clave es la fuente de verdad, asi que una etiqueta o unidad
    que cambie aqui se refleja sola en la base sin escribir una migracion.
    """
    with engine.begin() as conn:
        for kpi in KPI_REGISTRY:
            conn.execute(
                text(
                    """
                    INSERT INTO kpi_definition (clave, etiqueta, modulo, dimensiones, unidad, created_by)
                    VALUES (:clave, :etiqueta, :modulo, CAST(:dimensiones AS jsonb), :unidad, 1)
                    ON CONFLICT (clave) DO UPDATE SET
                        etiqueta = EXCLUDED.etiqueta,
                        modulo = EXCLUDED.modulo,
                        dimensiones = EXCLUDED.dimensiones,
                        unidad = EXCLUDED.unidad,
                        last_update_date = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "clave": kpi.clave,
                    "etiqueta": kpi.etiqueta,
                    "modulo": kpi.modulo,
                    "dimensiones": json.dumps(list(kpi.dimensiones)),
                    "unidad": kpi.unidad,
                },
            )
