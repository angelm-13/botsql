from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status, User
from app.models.session import transaction_context


ISSUER_RFC = "AAA010101AAA"
RECEIVER_RFC = "XAXX010101000"
QUOTATION_REFERENCE = "DEMO-COT-001"
MANUAL_REFERENCE = "DEMO-MAN-001"


def _first_or_create(db, model, filters, values):
    item = db.scalars(select(model).filter_by(**filters)).first()
    if item:
        return item
    item = model(**values)
    db.add(item)
    db.flush()
    return item


def _create_invoice(db, *, reference, status_name, actor_id, project, issuer, receiver, status, manual_capture, description, amount):
    existing = db.scalars(select(Invoice).where(Invoice.fiscal_reference == reference)).first()
    if existing:
        return existing
    emitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    subtotal = Decimal(str(amount)).quantize(Decimal("0.01"))
    tax = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"))
    invoice = Invoice(
        date_emision=emitted_at,
        date_expiration=emitted_at + timedelta(days=30),
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        descuento=Decimal("0"),
        isr_retention=Decimal("0"),
        iva_retention=Decimal("0"),
        invoice_status=status_name,
        payment_method="03",
        forma_pago="03",
        metodo_pago="PUE",
        uso_cfdi="G03",
        note="Escenario fiscal demo Tyakxa",
        id_customer_supplier=receiver.id_customer_supplier,
        id_issuer_customer_supplier=issuer.id_customer_supplier,
        id_proyect=project.id_proyect,
        fiscal_reference=reference,
        internationalization="local",
        currency="MXN",
        type_exchange_rate=Decimal("1"),
        tax_certification_supplier=issuer.id_customer_supplier,
        id_status=status.id_status,
        created_by=actor_id,
        nombre_emisor=issuer.name,
        lugar_expedicion=issuer.postal_code,
        tipo_de_comprobante="factura",
        rfc_receptor=receiver.tax_id,
        nombre_receptor=receiver.name,
        regimen_fiscal_receptor=receiver.fiscal_type,
        domicilio_fiscal_receptor=receiver.postal_code,
        exportacion="01",
        apply_tax=True,
        tax_rate=Decimal("16"),
        manual_capture=manual_capture,
    )
    db.add(invoice)
    db.flush()
    db.add(InvoiceMaterialService(
        id_invoice=invoice.id_invoice,
        invoice_material_service_description=description,
        is_directly_related_to_product_service_creation=False,
        id_authorized=actor_id,
        id_status=status.id_status,
        id_buyer=actor_id,
        id_customer_supplier=receiver.id_customer_supplier,
        gross_price=subtotal,
        quantity=Decimal("1"),
        created_by=actor_id,
        line_type="custom",
        tax_applicable=True,
        line_tax=tax,
        line_total=subtotal + tax,
        authorization_status="authorized",
        authorization_date=emitted_at,
        discount=Decimal("0"),
        sat_product_key="80101500",
        sat_unit_key="E48",
        tax_object="02",
        tax_rate=Decimal("16"),
        isr_retention_rate=Decimal("0"),
        iva_retention_rate=Decimal("0"),
    ))
    return invoice


def seed_fiscal_demo(actor_id=None):
    with transaction_context() as db:
        actor = db.get(User, actor_id) if actor_id else db.scalars(
            select(User).where(User.deletion_date.is_(None)).order_by(User.id_user)
        ).first()
        if not actor:
            raise RuntimeError("Crea primero un usuario administrador con python init_db.py")
        actor_id = actor.id_user
        status = _first_or_create(db, Status, {"status_description": "Fiscal demo"}, {
            "status_description": "Fiscal demo", "category": "invoice", "is_terminal": False,
            "sort_order": "asc", "created_by": actor_id,
        })
        issuer = _first_or_create(db, CustomerSupplier, {"tax_id": ISSUER_RFC}, {
            "name": "Servicios Demo del Centro SA de CV", "postal_code": "06600", "fiscal_type": "601",
            "tax_id": ISSUER_RFC, "type": "supplier", "email": "facturacion@demo.local",
            "id_user": actor_id, "created_by": actor_id,
        })
        receiver = _first_or_create(db, CustomerSupplier, {"tax_id": RECEIVER_RFC}, {
            "name": "Cliente Publico Demo", "postal_code": "06600", "fiscal_type": "616",
            "tax_id": RECEIVER_RFC, "type": "client", "email": "cliente@demo.local",
            "id_user": actor_id, "created_by": actor_id,
        })
        project = _first_or_create(db, Proyect, {"title": "Demo fiscal 2026"}, {
            "id_customer_supplier": receiver.id_customer_supplier, "leader": actor_id,
            "proyect_description": "Escenario para probar cotizacion, factura manual, XML y PDF",
            "title": "Demo fiscal 2026", "proyect_status": "in_progress", "created_by": actor_id,
        })
        quotation = _create_invoice(
            db, reference=QUOTATION_REFERENCE, status_name="Cotizacion", actor_id=actor_id,
            project=project, issuer=issuer, receiver=receiver, status=status, manual_capture=False,
            description="Consultoria de implementacion", amount="2500.00",
        )
        manual = _create_invoice(
            db, reference=MANUAL_REFERENCE, status_name="pendiente", actor_id=actor_id,
            project=project, issuer=issuer, receiver=receiver, status=status, manual_capture=True,
            description="Servicio de soporte mensual", amount="1200.00",
        )
        db.flush()
        return {
            "issuer_id": issuer.id_customer_supplier,
            "receiver_id": receiver.id_customer_supplier,
            "project_id": project.id_proyect,
            "quotation_id": quotation.id_invoice,
            "manual_invoice_id": manual.id_invoice,
        }


if __name__ == "__main__":
    print(seed_fiscal_demo())