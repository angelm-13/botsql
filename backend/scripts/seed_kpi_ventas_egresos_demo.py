"""Seed de datos de prueba para ventas_por_empleado / egresos_por_empleado.

Por que existe
--------------
Los dos KPIs de facturacion (`app/kpis/registry.py`) se calculan sobre
`invoice`, pero la base de dev solo trae un registro de bootstrap con
`invoice_status = 'test state'` (valor invalido) y `deletion_date` poblado --
no pasa ni el filtro de borrado de ninguno de los dos KPIs. Sin datos que
cumplan el filtro no hay forma de probar el calculo con datos reales.

Este script crea 3 usuarios de prueba (idempotente por `username`) y ~26
facturas repartidas en las ultimas ~8 semanas, con estatus siempre vigentes
(nunca `cotizacion`/`cancelada`, nunca con `deletion_date` poblado) y
`invoice_direction` variado entre venta normal (NULL, el camino normal de
`manual_invoice_service`) y `compra` (para poder probar `egresos_por_empleado`
con el mismo lote). Reutiliza `customer_supplier`/`status` de bootstrap
(id 1) en vez de crear catalogos nuevos, igual que `seed_fiscal_demo.py`.

Es idempotente: si ya corrio antes (se detecta por el `note` marcador), no
vuelve a insertar y solo reporta lo que ya existe.
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.models import CustomerSupplier, Invoice, Status, User
from app.models.session import transaction_context

ADMIN_ID = 1
NOTE_MARCADOR = "Seed demo KPI ventas/egresos"
USUARIOS_DEMO = (
    {"username": "kpi-demo-ventas-1", "full_name": "Empleado Demo KPI 1"},
    {"username": "kpi-demo-ventas-2", "full_name": "Empleado Demo KPI 2"},
    {"username": "kpi-demo-ventas-3", "full_name": "Empleado Demo KPI 3"},
)
ESTATUS_VIGENTES = ("pendiente", "parcial", "pagada", "timbrada")
MONTOS = (1250.50, 3200.00, 890.75, 15600.00, 4300.25, 720.00, 9800.50, 2100.00, 5400.00, 675.25)
NUM_FACTURAS = 26
DIAS_RANGO = 56  # ~8 semanas, dentro de los ultimos 2 meses


def _first_or_create(db, model, filters, values):
    item = db.scalars(select(model).filter_by(**filters)).first()
    if item:
        return item
    item = model(**values)
    db.add(item)
    db.flush()
    return item


def _ensure_test_users(db):
    usuarios = []
    for datos in USUARIOS_DEMO:
        usuario = _first_or_create(db, User, {"username": datos["username"]}, {
            "username": datos["username"],
            "full_name": datos["full_name"],
            "created_by": ADMIN_ID,
            "id_permission": 3,
            "id_proyect": 1,
            "id_status": 1,
            "supervisor": ADMIN_ID,
            "user_type": "employee",
            "is_employee": True,
        })
        usuarios.append(usuario)
    return usuarios


def seed_kpi_ventas_egresos_demo():
    with transaction_context() as db:
        customer = db.get(CustomerSupplier, 1)
        status = db.get(Status, 1)
        if customer is None or status is None:
            raise RuntimeError(
                "Faltan los catalogos bootstrap (customer_supplier=1 / status=1); "
                "corre init_db.py primero."
            )

        usuarios = _ensure_test_users(db)
        db.flush()

        existentes = db.scalars(
            select(Invoice).where(Invoice.note == NOTE_MARCADOR)
        ).all()
        if existentes:
            fechas = [factura.date_emision for factura in existentes]
            return {
                "usuarios": [u.id_user for u in usuarios],
                "facturas_creadas": 0,
                "facturas_ya_existentes": len(existentes),
                "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()),
            }

        hoy = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        inicio_rango = hoy - timedelta(days=DIAS_RANGO)

        rng = random.Random(20260908)  # seed fija: seed reproducible entre corridas
        facturas = []
        for i in range(NUM_FACTURAS):
            fecha = inicio_rango + timedelta(
                days=rng.randint(0, DIAS_RANGO), hours=rng.randint(8, 18), minutes=rng.randint(0, 59),
            )
            empleado = usuarios[i % len(usuarios)]
            invoice_status = rng.choice(ESTATUS_VIGENTES)
            # ~1 de cada 4 es egreso (invoice_direction='compra'); el resto se
            # queda con invoice_direction=NULL, el camino normal de venta
            # manual (ver el docstring de ventas_por_empleado_query). Se
            # decide con un sorteo aparte del de invoice_status para que no
            # queden correlacionados (con el mismo modulo, todas las 'compra'
            # terminaban con el mismo estatus).
            invoice_direction = "compra" if rng.random() < 0.25 else None
            subtotal = Decimal(str(rng.choice(MONTOS)))
            tax = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"))

            facturas.append(Invoice(
                date_emision=fecha,
                subtotal=subtotal,
                tax=tax,
                total=subtotal + tax,
                invoice_status=invoice_status,
                invoice_direction=invoice_direction,
                id_customer_supplier=customer.id_customer_supplier,
                id_issuer_customer_supplier=customer.id_customer_supplier,
                tax_certification_supplier=customer.id_customer_supplier,
                id_status=status.id_status,
                created_by=empleado.id_user,
                apply_tax=True,
                tax_rate=Decimal("16"),
                note=NOTE_MARCADOR,
            ))
        db.add_all(facturas)
        db.flush()

        fechas = [factura.date_emision for factura in facturas]
        return {
            "usuarios": [u.id_user for u in usuarios],
            "facturas_creadas": len(facturas),
            "facturas_ya_existentes": 0,
            "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()),
        }


if __name__ == "__main__":
    print(seed_kpi_ventas_egresos_demo())
