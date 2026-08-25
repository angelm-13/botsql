from __future__ import annotations

import base64
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.models.customer_supplier import CustomerSupplier
from app.models.invoice import Invoice
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.stamping_operation import StampingOperation
from app.models.session import transaction_context
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_builder import build_draft, validate_draft
from app.services.invoice_artifacts import build_fake_cfdi_xml, save_invoice_xml
from app.utils.errors import AppError


@dataclass(frozen=True)
class StampingResult:
    status: str
    reference: str | None = None
    metadata: dict | None = None
    error_code: str | None = None
    xml: str | bytes | None = None


class StampingProvider:
    name = "base"

    def stamp(self, payload, idempotency_key):
        raise NotImplementedError

    def reconcile(self, reference):
        raise NotImplementedError


class FakeStampingProvider(StampingProvider):
    name = "fake"

    def __init__(self, result=None):
        self.result = result
        self.calls = 0

    def stamp(self, payload, idempotency_key):
        self.calls += 1
        if self.result:
            return self.result
        stamp_uuid, xml = build_fake_cfdi_xml(payload)
        return StampingResult("stamped", stamp_uuid, {"environment": "test", "has_xml": True}, xml=xml)

    def reconcile(self, reference):
        return self.result or StampingResult("uncertain", reference, error_code="reconciliation_required")


class FacturamaSandboxProvider(StampingProvider):
    name = "facturama_sandbox"

    def __init__(self, base_url=None, username=None, password=None, timeout=15, expedition_place=None, name_id=None):
        self.base_url = (base_url or os.getenv("FACTURAMA_BASE_URL") or "https://apisandbox.facturama.mx").rstrip("/")
        self.username = username or os.getenv("FACTURAMA_USERNAME") or os.getenv("FACTURAMA_USER") or ""
        self.password = password or os.getenv("FACTURAMA_PASSWORD") or os.getenv("FACTURAMA_PASS") or ""
        self.expedition_place = expedition_place or os.getenv("FACTURAMA_EXPEDITION_PLACE") or ""
        self.name_id = name_id or os.getenv("FACTURAMA_NAME_ID") or "1"
        self.timeout = timeout
        if not self.base_url.startswith("https://"):
            raise ValueError("FACTURAMA_BASE_URL must use HTTPS")

    def _authorization_header(self):
        credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return f"Basic {credentials}"

    def test_connection(self):
        if not self.username or not self.password:
            return False, "Faltan usuario y/o contraseña de Facturama."
        request = Request(
            f"{self.base_url}/Client",
            headers={"Authorization": self._authorization_header()},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200, "Conexión exitosa con Facturama."
        except HTTPError as exc:
            if exc.code in (401, 403):
                return False, "Usuario o contraseña incorrectos."
            return False, f"Facturama respondió {exc.code}."
        except (TimeoutError, socket.timeout, URLError) as exc:
            return False, f"No se pudo conectar con Facturama: {exc.reason if isinstance(exc, URLError) else exc}"

    def build_request_body(self, payload):
        items = []
        for concept in payload.get("concepts") or []:
            quantity = Decimal(str(concept.get("quantity") or 0))
            unit_price = Decimal(str(concept.get("unit_price") or 0))
            subtotal = Decimal(str(concept.get("amount") or quantity * unit_price))
            discount = min(max(Decimal(str(concept.get("discount") or 0)), Decimal("0")), subtotal)
            tax_base = subtotal - discount
            iva_rate = Decimal(str(concept.get("iva_rate") or 0))
            isr_rate = Decimal(str(concept.get("isr_retention_rate") or 0))
            iva_retention_rate = Decimal(str(concept.get("iva_retention_rate") or 0))
            tax_object = str(concept.get("tax_object") or "01")
            taxes = []
            if tax_object == "02":
                taxes.append({
                    "Total": f"{tax_base * iva_rate:.2f}", "Name": "IVA", "Base": f"{tax_base:.2f}",
                    "Rate": f"{iva_rate:.6f}", "IsRetention": "false", "IsFederalTax": "true",
                })
            if isr_rate > 0:
                taxes.append({
                    "Total": f"{tax_base * isr_rate:.2f}", "Name": "ISR", "Base": f"{tax_base:.2f}",
                    "Rate": f"{isr_rate:.6f}", "IsRetention": "true", "IsFederalTax": "true",
                })
            if iva_retention_rate > 0:
                taxes.append({
                    "Total": f"{tax_base * iva_retention_rate:.2f}", "Name": "IVA", "Base": f"{tax_base:.2f}",
                    "Rate": f"{iva_retention_rate:.6f}", "IsRetention": "true", "IsFederalTax": "true",
                })
            total = tax_base + (tax_base * iva_rate if tax_object == "02" else 0) - tax_base * isr_rate - tax_base * iva_retention_rate
            item = {
                "Quantity": format(quantity, "f"), "ProductCode": concept.get("sat_product_key"),
                "UnitCode": concept.get("sat_unit_key"), "Unit": concept.get("sat_unit_key"),
                "Description": concept.get("description"), "UnitPrice": f"{unit_price:.2f}",
                "Subtotal": f"{subtotal:.2f}", "TaxBase": f"{tax_base:.2f}",
                "TaxObject": tax_object, "Total": f"{total:.2f}",
            }
            if discount:
                item["Discount"] = f"{discount:.2f}"
            if taxes:
                item["Taxes"] = taxes
            items.append(item)

        issuer = payload.get("issuer") or {}
        receiver = payload.get("receiver") or {}
        body = {
            "CfdiType": payload.get("cfdi_type") or "I", "NameId": self.name_id,
            "ExpeditionPlace": self.expedition_place or issuer.get("postal_code"), "Exportation": "01",
            "PaymentForm": payload.get("payment_form"), "PaymentMethod": payload.get("payment_method"),
            "Currency": payload.get("currency") or "MXN",
            "Receiver": {
                "Rfc": receiver.get("rfc"), "Name": receiver.get("name"),
                "CfdiUse": receiver.get("cfdi_use"), "FiscalRegime": receiver.get("tax_regime"),
                "TaxZipCode": receiver.get("postal_code"),
            },
            "Items": items,
        }
        if payload.get("series"):
            body["Serie"] = payload["series"]
        if payload.get("folio"):
            body["Folio"] = payload["folio"]
        if payload.get("payment_conditions"):
            body["PaymentConditions"] = str(payload["payment_conditions"])[:1000]
        return body

    def stamp(self, payload, idempotency_key):
        if not self.username or not self.password:
            return StampingResult("rejected", error_code="facturama_credentials_missing")
        body = json.dumps(self.build_request_body(payload)).encode("utf-8")
        request = Request(
            f"{self.base_url}/3/cfdis",
            data=body,
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            stamp = data.get("Complement", {}).get("TaxStamp", {})
            reference = stamp.get("Uuid") or data.get("Uuid") or data.get("Id")
            return StampingResult("stamped", reference, {"http_status": response.status, "facturama_id": data.get("Id")}, xml=data.get("Xml"))
        except HTTPError as exc:
            return StampingResult("rejected", error_code=f"http_{exc.code}", metadata={"http_status": exc.code})
        except (TimeoutError, socket.timeout, URLError):
            return StampingResult("uncertain", error_code="provider_timeout")

    def reconcile(self, reference):
        return StampingResult("uncertain", reference, error_code="reconciliation_required")


def configured_provider():
    from app.services.pac_config_service import provider_credentials

    credentials = provider_credentials()
    provider_name = credentials["provider"]
    if provider_name == "fake":
        return FakeStampingProvider()
    if provider_name in {"facturama_sandbox", "facturama"}:
        provider = FacturamaSandboxProvider(
            base_url=credentials["base_url"], username=credentials["username"], password=credentials["password"],
            expedition_place=credentials["expedition_place"], name_id=credentials["name_id"],
        )
        provider.name = provider_name
        return provider
    raise ValueError("Unsupported STAMPING_PROVIDER")


def stamp_invoice(invoice_id, idempotency_key, user_data, provider=None):
    key = str(idempotency_key or "").strip()
    if not key or len(key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})
    provider = provider or configured_provider()

    with transaction_context() as db:
        previous = db.scalars(select(StampingOperation).where(StampingOperation.idempotency_key == key)).first()
        if previous:
            if previous.id_invoice != int(invoice_id):
                raise AppError("errors.idempotency_conflict", 409)
            return previous.serialize(), False

        invoice = db.get(Invoice, invoice_id)
        if not invoice or not invoice.id_proyect:
            raise AppError("errors.resource_not_found", 404)
        actor_project = user_data.get("id_proyect") or user_data.get("project_id")
        unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
        if not unrestricted and str(actor_project) != str(invoice.id_proyect):
            raise AppError("errors.permission_denied", 403)

        issuer = db.get(CustomerSupplier, invoice.id_issuer_customer_supplier)
        receiver = db.get(CustomerSupplier, invoice.id_customer_supplier)
        lines = db.scalars(
            select(InvoiceMaterialService).where(
                InvoiceMaterialService.id_invoice == invoice.id_invoice,
                InvoiceMaterialService.authorization_status == "authorized",
                InvoiceMaterialService.deletion_date.is_(None),
            )
        ).all()
        if not issuer or not receiver:
            raise AppError("errors.resource_not_found", 404)
        draft = build_draft(invoice, issuer, receiver, lines)
        validation_errors = validate_draft(draft)
        if validation_errors:
            raise AppError("invoice.stamping_validation_failed", 400, {"errors": validation_errors})

        operation = StampingOperation(
            id_invoice=invoice.id_invoice,
            id_proyect=invoice.id_proyect,
            idempotency_key=key,
            provider=provider.name,
            status="processing",
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(operation)
        db.flush()
        result = provider.stamp(draft.serialize(), key)
        operation.status = result.status
        operation.provider_reference = result.reference
        operation.response_metadata = result.metadata
        operation.error_code = result.error_code
        if result.status == "stamped":
            if not result.reference:
                raise AppError("invoice.stamping_missing_uuid", 502)
            invoice.invoice_status = "timbrada"
            invoice.folio_fiscal = result.reference
            invoice.certification_date = datetime.now(timezone.utc).replace(tzinfo=None)
            if result.xml:
                fiscal_data = parse_cfdi(result.xml.encode("utf-8") if isinstance(result.xml, str) else result.xml)
                if fiscal_data["uuid"] != str(result.reference).upper():
                    raise AppError("invoice.stamping_uuid_mismatch", 502)
                save_invoice_xml(invoice.id_invoice, result.xml)
                invoice.cfdi_code = fiscal_data["uuid"]
                invoice.no_certificado = fiscal_data.get("no_certificado")
                invoice.no_certificado_sat = fiscal_data.get("no_certificado_sat")
                invoice.sello_sat = fiscal_data.get("sello_sat")
                invoice.certification_date = datetime.fromisoformat(fiscal_data["certification_date"])
        db.flush()
        return operation.serialize(), True