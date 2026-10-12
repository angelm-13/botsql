from __future__ import annotations

import base64
import json
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.models.customer_supplier import CustomerSupplier
from app.models.invoice import Invoice
from app.models.invoice_folio_counter import InvoiceFolioCounter
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.stamping_operation import StampingOperation
from app.models.session import transaction_context
from app.services.cfdi_validation import validate_cfdi_xml
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_builder import build_draft, inspect_draft
from app.services.invoice_catalogs import CLAVE_UNIDAD_FRECUENTES, OBJETO_IMP_CON_DESGLOSE, RFC_PUBLICO_GENERAL
from app.services.cfdi_xml_store import save_cfdi_xml
from app.services.invoice_artifacts import build_fake_cfdi_xml
from app.utils.errors import AppError


def _cents(value) -> Decimal:
    """Redondea a dos decimales, como exige el Anexo 20 para MXN."""
    return Decimal(str(value if value not in (None, "") else 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@dataclass(frozen=True)
class CancellationResult:
    """Respuesta del PAC a una solicitud de cancelacion.

    `acknowledgement` es el acuse que devuelve el SAT: el comprobante de que la
    cancelacion se solicito y con que resultado. Sin el no hay como demostrar
    ante una revision que se pidio.
    """

    status: str
    reference: str | None = None
    acknowledgement: str | None = None
    metadata: dict | None = None
    error_code: str | None = None


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

    def stamp_payment_complement(self, payload, idempotency_key):
        """Timbra el complemento de pago (REP) de un abono."""
        raise NotImplementedError

    def reconcile(self, reference):
        raise NotImplementedError

    def cancel(self, payload, idempotency_key):
        """Solicita al SAT la cancelacion de un comprobante."""
        raise NotImplementedError

    def cancellation_status(self, reference):
        """Consulta si una solicitud en proceso ya se resolvio."""
        raise NotImplementedError


class FakeStampingProvider(StampingProvider):
    name = "fake"

    def __init__(self, result=None, cancellation_result=None):
        self.result = result
        self.cancellation_result = cancellation_result
        self.calls = 0
        self.cancellations = 0

    def stamp(self, payload, idempotency_key):
        self.calls += 1
        if self.result:
            return self.result
        stamp_uuid, xml = build_fake_cfdi_xml(payload)
        return StampingResult("stamped", stamp_uuid, {"environment": "test", "has_xml": True}, xml=xml)

    def stamp_payment_complement(self, payload, idempotency_key):
        self.calls += 1
        if self.result:
            return self.result
        # A diferencia de stamp(): el generador de XML fake todavia no arma
        # el nodo Complemento.Payments de un comprobante tipo P, y no hace
        # falta para probar exito/fallo/rollback de la orquestacion.
        return StampingResult("stamped", str(uuid.uuid4()).upper(), {"environment": "test"})

    def reconcile(self, reference):
        return self.result or StampingResult("uncertain", reference, error_code="reconciliation_required")

    def cancel(self, payload, idempotency_key):
        """Cancela de inmediato, salvo que se le pida simular la espera.

        El SAT deja "en proceso" las cancelaciones que necesitan que el
        receptor acepte. `cancellation_result` permite reproducir ese caso y el
        del rechazo, que son los que suelen quedar sin probar.
        """
        self.cancellations += 1
        if self.cancellation_result:
            return self.cancellation_result
        return CancellationResult(
            "cancelado",
            reference=str(payload.get("uuid") or ""),
            acknowledgement=f"ACUSE-{payload.get('uuid') or 'SIN-UUID'}",
            metadata={"environment": "test", "motive": payload.get("motive")},
        )

    def cancellation_status(self, reference):
        return self.cancellation_result or CancellationResult(
            "cancelado", reference=reference, acknowledgement=f"ACUSE-{reference}"
        )


class FacturamaSandboxProvider(StampingProvider):
    name = "facturama_sandbox"
    # Atributo de clase para que FacturamaMultiemisorProvider pueda
    # sobreescribir solo la ruta (vive bajo /api-lite) sin duplicar stamp().
    CFDIS_PATH = "/3/cfdis"

    def __init__(self, base_url=None, username=None, password=None, timeout=15, name_id=None):
        self.base_url = (base_url or os.getenv("FACTURAMA_BASE_URL") or "https://apisandbox.facturama.mx").rstrip("/")
        self.username = username or os.getenv("FACTURAMA_USERNAME") or os.getenv("FACTURAMA_USER") or ""
        self.password = password or os.getenv("FACTURAMA_PASSWORD") or os.getenv("FACTURAMA_PASS") or ""
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
            # Los importes vienen ya redondeados por partida desde el borrador;
            # recalcularlos aqui reintroduciria los descuadres de centavos que
            # el SAT rechaza.
            quantity = Decimal(str(concept.get("quantity") or 0))
            unit_price = Decimal(str(concept.get("unit_price") or 0))
            subtotal = _cents(concept.get("amount") or quantity * unit_price)
            discount = _cents(concept.get("discount") or 0)
            tax_base = _cents(concept.get("taxable_base") or (subtotal - discount))
            iva_rate = Decimal(str(concept.get("iva_rate") or 0))
            isr_rate = Decimal(str(concept.get("isr_retention_rate") or 0))
            iva_retention_rate = Decimal(str(concept.get("iva_retention_rate") or 0))
            tax_object = str(concept.get("tax_object") or "01")
            is_exempt = bool(concept.get("iva_exempt"))
            # `breaks_down_taxes` y los importes ya redondeados llegan en el
            # payload del borrador; si el llamador armo el dict a mano se
            # derivan del ObjetoImp y de las tasas.
            breaks_down = concept.get("breaks_down_taxes")
            if breaks_down is None:
                breaks_down = tax_object in OBJETO_IMP_CON_DESGLOSE
            transferred_iva = _cents(concept.get("transferred_iva", tax_base * iva_rate))
            retained_isr = _cents(concept.get("retained_isr", tax_base * isr_rate))
            retained_iva = _cents(concept.get("retained_iva", tax_base * iva_retention_rate))
            taxes = []
            if breaks_down:
                iva_entry = {
                    "Name": "IVA", "Base": f"{tax_base:.2f}",
                    "IsRetention": "false", "IsFederalTax": "true",
                }
                if is_exempt:
                    # Facturama declara el exento con Name "IVA Exento", que el
                    # PAC traduce a TipoFactor="Exento" en el XML. Mandarlo como
                    # "IVA" con tasa 0 emitiria tasa cero, que el SAT considera
                    # distinto. Mapeo verificado contra el sandbox.
                    iva_entry.update({"Name": "IVA Exento", "Total": "0.00", "Rate": "0.000000"})
                else:
                    iva_entry.update({"Total": f"{transferred_iva:.2f}", "Rate": f"{iva_rate:.6f}"})
                taxes.append(iva_entry)
                if isr_rate > 0:
                    taxes.append({
                        "Total": f"{retained_isr:.2f}", "Name": "ISR", "Base": f"{tax_base:.2f}",
                        "Rate": f"{isr_rate:.6f}", "IsRetention": "true", "IsFederalTax": "true",
                    })
                if iva_retention_rate > 0:
                    taxes.append({
                        "Total": f"{retained_iva:.2f}", "Name": "IVA", "Base": f"{tax_base:.2f}",
                        "Rate": f"{iva_retention_rate:.6f}", "IsRetention": "true", "IsFederalTax": "true",
                    })
            total = _cents(concept.get("total", tax_base + transferred_iva - retained_isr - retained_iva))
            unit_key = str(concept.get("sat_unit_key") or "")
            item = {
                "Quantity": format(quantity, "f"), "ProductCode": concept.get("sat_product_key"),
                # UnitCode es la ClaveUnidad del SAT; Unit es la etiqueta legible
                # que Facturama imprime en el PDF.
                "UnitCode": unit_key, "Unit": CLAVE_UNIDAD_FRECUENTES.get(unit_key, unit_key),
                "Description": concept.get("description"), "UnitPrice": format(unit_price, "f"),
                "Subtotal": f"{subtotal:.2f}",
                "TaxObject": tax_object, "Total": f"{total:.2f}",
            }
            if discount:
                item["Discount"] = f"{discount:.2f}"
            if taxes:
                item["Taxes"] = taxes
            items.append(item)

        issuer = payload.get("issuer") or {}
        receiver = payload.get("receiver") or {}
        currency = str(payload.get("currency") or "MXN").upper()
        body = {
            "CfdiType": payload.get("cfdi_type") or "I", "NameId": self.name_id,
            # Siempre el domicilio de la empresa emisora, nunca una config
            # global de cuenta -- una cuenta puede timbrar por mas de un RFC
            # (multiemisor), y aunque no lo sea, capturarlo aparte de la ficha
            # de la empresa solo invita a que los dos se desincronicen.
            "ExpeditionPlace": issuer.get("postal_code"),
            "Exportation": str(payload.get("export_code") or "01"),
            "PaymentForm": payload.get("payment_form"), "PaymentMethod": payload.get("payment_method"),
            "Currency": currency,
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
        if currency not in {"MXN", "XXX"}:
            # Confirmado contra el sandbox real: Facturama exige este nombre
            # exacto -- "ExchangeRate" (el que se usaba antes) lo rechaza con
            # "Este campo es requerido", asi que ninguna factura en moneda
            # extranjera habia timbrado nunca de verdad.
            body["CurrencyExchangeRate"] = format(Decimal(str(payload.get("exchange_rate") or 1)), "f")
        if receiver.get("rfc") == RFC_PUBLICO_GENERAL:
            # Confirmado contra el sandbox real: sin este nodo Facturama
            # rechaza cualquier comprobante cuyo receptor sea el RFC generico
            # de publico en general -- no documentado en la guia, y hasta
            # ahora ningun timbrado a ese receptor habia funcionado de
            # verdad.
            now = datetime.now(timezone.utc)
            body["GlobalInformation"] = {
                "Periodicity": "01", "Months": f"{now.month:02d}", "Year": str(now.year),
            }
        return body

    def stamp(self, payload, idempotency_key):
        if not self.username or not self.password:
            return StampingResult("rejected", error_code="facturama_credentials_missing")
        return self._post_cfdi(self.build_request_body(payload), idempotency_key)

    def build_payment_complement_request_body(self, payload):
        """Arma el body del REP (CfdiType=P) -- formato confirmado con
        timbrado real contra el sandbox de Facturama, no solo con su guia:
        `Folio` es obligatorio, y `GlobalInformation` hace falta si el
        receptor es el RFC generico de publico en general (aplica igual a
        tipo P que a tipo I, aunque la guia solo lo menciona para I).
        """
        issuer = payload.get("issuer") or {}
        receiver = payload.get("receiver") or {}
        payment = payload.get("payment") or {}
        related = payload.get("related_document") or {}
        currency = str(payment.get("currency") or "MXN").upper()

        payment_node = {
            "Date": payment.get("paid_at"),
            "PaymentForm": payment.get("payment_form"),
            "Amount": payment.get("amount"),
        }
        related_node = {
            "TaxObject": "01",
            "Uuid": related.get("uuid"),
            "Folio": related.get("folio"),
            "PaymentMethod": related.get("payment_method"),
            "PartialityNumber": str(related.get("instalment") or ""),
            "PreviousBalanceAmount": related.get("previous_balance"),
            "AmountPaid": related.get("amount_paid"),
            "ImpSaldoInsoluto": related.get("outstanding_balance"),
        }
        if related.get("series"):
            related_node["Serie"] = related["series"]
        if currency not in {"MXN", "XXX"}:
            payment_node["Currency"] = currency
            # Confirmado contra el sandbox real: nombre de campo propio del
            # nodo Payments, distinto de "CurrencyExchangeRate" a nivel raiz
            # -- sin el, rechazo "El atributo ExchangeRate es requerido".
            payment_node["ExchangeRate"] = payment.get("exchange_rate")
            related_node["Currency"] = currency
            # EquivalenceDocRel aceptado por Facturama en la prueba en vivo,
            # pero la reconciliacion exacta de importes con dos monedas
            # distintas (documento vs pago) quedo sin resolver del todo --
            # ver notas de la sesion antes de confiar en este calculo a
            # ciegas con un caso real de conversion cruzada.
            related_node["EquivalenceDocRel"] = payment.get("exchange_rate")
        if payment.get("operation_number"):
            payment_node["OperationNumber"] = payment["operation_number"]
        payment_node["RelatedDocuments"] = [related_node]

        body = {
            "CfdiType": "P",
            "NameId": self.name_id,
            "ExpeditionPlace": issuer.get("postal_code"),
            "Folio": payload.get("folio"),
            "Receiver": {
                "Rfc": receiver.get("rfc"), "Name": receiver.get("name"),
                "CfdiUse": "CP01", "FiscalRegime": receiver.get("tax_regime"),
                "TaxZipCode": receiver.get("postal_code"),
            },
            "Complemento": {"Payments": [payment_node]},
        }
        if receiver.get("rfc") == RFC_PUBLICO_GENERAL:
            emision = str(payment.get("paid_at") or "")
            body["GlobalInformation"] = {
                "Periodicity": "01",
                "Months": emision[5:7] if len(emision) >= 7 else "01",
                "Year": emision[:4] if len(emision) >= 4 else "",
            }
        return body

    def stamp_payment_complement(self, payload, idempotency_key):
        if not self.username or not self.password:
            return StampingResult("rejected", error_code="facturama_credentials_missing")
        return self._post_cfdi(self.build_payment_complement_request_body(payload), idempotency_key)

    def _post_cfdi(self, body, idempotency_key):
        data = json.dumps(body).encode("utf-8")
        request = Request(
            f"{self.base_url}{self.CFDIS_PATH}",
            data=data,
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            stamp = result.get("Complement", {}).get("TaxStamp", {})
            reference = stamp.get("Uuid") or result.get("Uuid") or result.get("Id")
            return StampingResult("stamped", reference, {"http_status": response.status, "facturama_id": result.get("Id")}, xml=result.get("Xml"))
        except HTTPError as exc:
            # El motivo del rechazo viaja en el cuerpo de la respuesta: sin el,
            # un 400 de validacion no dice que corregir.
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
            except Exception:
                detail = ""
            return StampingResult(
                "rejected",
                error_code=f"http_{exc.code}",
                metadata={"http_status": exc.code, "provider_response": detail},
            )
        except (TimeoutError, socket.timeout, URLError):
            return StampingResult("uncertain", error_code="provider_timeout")

    def reconcile(self, reference):
        return StampingResult("uncertain", reference, error_code="reconciliation_required")

    def cancel(self, payload, idempotency_key):
        """Solicita la cancelacion al PAC.

        Facturama cancela por folio fiscal, con el motivo y -solo en el motivo
        01- el folio del comprobante que sustituye. La respuesta puede venir ya
        cancelada o "en proceso" si el receptor tiene que aceptar.
        """
        if not self.username or not self.password:
            return CancellationResult("solicitada", error_code="facturama_credentials_missing")

        parametros = {"type": "issued", "motive": payload.get("motive")}
        if payload.get("substitution_uuid"):
            parametros["uuidReplacement"] = payload["substitution_uuid"]
        consulta = "&".join(f"{clave}={valor}" for clave, valor in parametros.items() if valor)
        request = Request(
            f"{self.base_url}/cfdi/{payload.get('uuid')}?{consulta}",
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="DELETE",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
            return CancellationResult(
                _cancellation_status_from_provider(data.get("Status")),
                reference=data.get("Uuid") or payload.get("uuid"),
                acknowledgement=data.get("Acuse") or data.get("acuse"),
                metadata={"http_status": response.status, "raw_status": data.get("Status")},
            )
        except HTTPError as exc:
            detalle = ""
            try:
                detalle = exc.read().decode("utf-8")[:500]
            except Exception:
                pass
            return CancellationResult(
                "solicitada",
                error_code=f"http_{exc.code}",
                metadata={"http_status": exc.code, "detail": detalle},
            )
        except (TimeoutError, socket.timeout, URLError):
            return CancellationResult("solicitada", error_code="provider_timeout")

    def cancellation_status(self, reference):
        if not self.username or not self.password:
            return CancellationResult("solicitada", error_code="facturama_credentials_missing")
        request = Request(
            f"{self.base_url}/cfdi/{reference}",
            headers={"Authorization": self._authorization_header()},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
            return CancellationResult(
                _cancellation_status_from_provider(data.get("Status")),
                reference=reference,
                acknowledgement=data.get("Acuse") or data.get("acuse"),
                metadata={"raw_status": data.get("Status")},
            )
        except (HTTPError, TimeoutError, socket.timeout, URLError):
            return CancellationResult("en_proceso", reference=reference, error_code="status_unavailable")


class FacturamaMultiemisorProvider(FacturamaSandboxProvider):
    """Timbrado multiemisor: una sola cuenta de Facturama que emite por cuenta
    de varios RFC.

    A diferencia de la cuenta API Web (`FacturamaSandboxProvider`): cada
    emisor necesita su CSD registrado en la cuenta (ver `upload_csd`), cada
    timbrado manda el nodo `Issuer` con el RFC/nombre/regimen del emisor en
    vez de depender de un `NameId` fijo por cuenta, y los endpoints viven
    bajo `/api-lite`.
    """

    name = "facturama_multiemisor"
    CFDIS_PATH = "/api-lite/3/cfdis"
    CSDS_PATH = "/api-lite/csds"

    def build_request_body(self, payload):
        body = super().build_request_body(payload)
        issuer = payload.get("issuer") or {}
        body["Issuer"] = {
            "Rfc": issuer.get("rfc"), "Name": issuer.get("name"),
            "FiscalRegime": issuer.get("tax_regime"),
        }
        # ExpeditionPlace ya viene del CP del emisor (el padre lo arma igual);
        # NameId es el perfil fiscal de la cuenta API Web, no aplica aqui.
        body.pop("NameId", None)
        return body

    def build_payment_complement_request_body(self, payload):
        body = super().build_payment_complement_request_body(payload)
        issuer = payload.get("issuer") or {}
        body["Issuer"] = {
            "Rfc": issuer.get("rfc"), "Name": issuer.get("name"),
            "FiscalRegime": issuer.get("tax_regime"),
        }
        body.pop("NameId", None)
        return body

    def upload_csd(self, rfc, cer_b64, key_b64, password):
        """Registra el CSD de un emisor en la cuenta de Facturama.

        Los archivos van en base64; Facturama custodia el CSD, tyakxa no lo
        guarda.
        """
        if not self.username or not self.password:
            return False, "Faltan credenciales de la cuenta del PAC."
        if not rfc:
            return False, "Falta el RFC del emisor."
        if not cer_b64 or not key_b64:
            return False, "Faltan los archivos del sello (.cer y .key)."

        body = json.dumps({
            "Rfc": rfc, "Certificate": cer_b64, "PrivateKey": key_b64,
            "PrivateKeyPassword": password or "",
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}{self.CSDS_PATH}",
            data=body,
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout):
                return True, "Sello digital registrado correctamente."
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                detail = ""
            # Idempotencia: si el CSD ya esta registrado para este RFC en la
            # cuenta, ese es justo el estado deseado -- Facturama lo rechaza
            # con 400 en vez de responder 200/201 de nuevo.
            if exc.code == 400 and "ya existe" in detail.lower():
                return True, "El sello digital ya estaba registrado en la cuenta; se reutiliza."
            return False, f"Facturama respondio {exc.code}: {detail}"
        except (TimeoutError, socket.timeout, URLError) as exc:
            return False, f"No se pudo conectar con Facturama: {exc}"

    def csd_registered(self, rfc):
        """Consulta si el emisor `rfc` ya tiene CSD registrado en la cuenta."""
        if not self.username or not self.password or not rfc:
            return False
        request = Request(
            f"{self.base_url}{self.CSDS_PATH}/{rfc}",
            headers={"Authorization": self._authorization_header()},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
        except (HTTPError, TimeoutError, socket.timeout, URLError):
            return False


# El PAC nombra los estados en ingles; aqui se traducen a los del sistema.
_CANCELLATION_STATUS_MAP = {
    "canceled": "cancelado",
    "cancelled": "cancelado",
    "cancelada": "cancelado",
    "inprocess": "en_proceso",
    "in_process": "en_proceso",
    "pending": "en_proceso",
    "rejected": "rechazado",
    "rechazada": "rechazado",
    "active": "rechazado",
    "vigente": "rechazado",
}


def _cancellation_status_from_provider(valor) -> str:
    """Traduce el estado del PAC. Lo desconocido queda en proceso.

    Se prefiere dejarlo "en proceso" antes que darlo por cancelado: un estado
    que no se entiende no puede tomarse como confirmacion, porque de ahi
    dependen la factura y la devolucion al almacen.
    """
    return _CANCELLATION_STATUS_MAP.get(str(valor or "").strip().lower().replace(" ", ""), "en_proceso")


def configured_provider():
    from app.services.pac_config_service import provider_credentials

    credentials = provider_credentials()
    provider_name = credentials["provider"]
    if provider_name == "fake":
        # Un proveedor de mentiras "timbra" CFDI que no existen: en produccion
        # una instalacion sin STAMPING_PROVIDER no debe caer aqui en silencio.
        from app.utils.startup_guard import is_production
        if is_production():
            raise AppError("stamping.fake_provider_not_allowed", 503)
        return FakeStampingProvider()
    if provider_name in {"facturama_sandbox", "facturama"}:
        provider = FacturamaSandboxProvider(
            base_url=credentials["base_url"], username=credentials["username"], password=credentials["password"],
            name_id=credentials["name_id"],
        )
        provider.name = provider_name
        return provider
    if provider_name in {"facturama_multiemisor_sandbox", "facturama_multiemisor"}:
        provider = FacturamaMultiemisorProvider(
            base_url=credentials["base_url"], username=credentials["username"], password=credentials["password"],
            name_id=credentials["name_id"],
        )
        provider.name = provider_name
        return provider
    raise ValueError("Unsupported STAMPING_PROVIDER")


def _max_folio_ya_usado(db, id_customer_supplier) -> int:
    """Mayor folio numerico ya usado por esta empresa emisora, o 0 si ninguno.

    Un cliente con datos migrados o con folios capturados a mano antes de
    que existiera este contador (torredigital-prod es un caso real
    confirmado: folios '1'-'11' ya en uso para su emisor principal) no debe
    recibir un contador que arranque en 1 a ciegas -chocaria de inmediato
    con esos folios ya existentes-.
    """
    folios = db.scalars(
        select(Invoice.folio).where(
            Invoice.id_issuer_customer_supplier == id_customer_supplier,
            Invoice.folio.isnot(None),
        )
    ).all()
    numericos = [int(f) for f in folios if str(f).strip().isdigit()]
    return max(numericos, default=0)


def _next_folio(db, id_customer_supplier) -> int:
    """Siguiente numero de folio para esta empresa emisora, sin repetir.

    `with_for_update()` bloquea la fila del contador mientras dura esta
    transaccion: si dos timbrados de la misma empresa entran a la vez, el
    segundo espera a que el primero termine de incrementar en vez de leer el
    mismo numero. En SQLite (solo pruebas) el lock no existe -no hace falta,
    las pruebas no timbran de verdad en paralelo-.
    """
    counter = (
        db.query(InvoiceFolioCounter)
        .filter(InvoiceFolioCounter.id_customer_supplier == id_customer_supplier)
        .with_for_update()
        .first()
    )
    if counter is None:
        inicio = _max_folio_ya_usado(db, id_customer_supplier) + 1
        counter = InvoiceFolioCounter(id_customer_supplier=id_customer_supplier, next_folio=inicio)
        db.add(counter)
        db.flush()
    folio = counter.next_folio
    counter.next_folio = folio + 1
    db.flush()
    return folio


def next_folio_if_missing(db, invoice) -> None:
    """Asigna folio consecutivo por empresa emisora, solo si nadie capturo uno.

    Comparado contra cotizador_demo (el sistema anterior de un cliente
    real): alla el timbrado siempre asigna un folio consecutivo real. Aqui
    `invoice.folio` era texto libre sin ningun control -cualquiera podia
    repetir numeros o dejarlo vacio-. No se sobreescribe un folio que ya
    trae dato (captura manual, dato migrado de un sistema anterior): el
    control automatico es para el caso comun, no para forzar un valor sobre
    quien de verdad necesita el suyo.
    """
    if str(invoice.folio or "").strip():
        return
    invoice.folio = str(_next_folio(db, invoice.id_issuer_customer_supplier))


def _load_draft(db, invoice_id, user_data):
    """Carga la factura, sus partidas autorizadas y arma el borrador CFDI."""
    invoice = db.get(Invoice, invoice_id)
    if not invoice or not invoice.id_proyect:
        raise AppError("errors.resource_not_found", 404)
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    if not unrestricted and str(actor_project) != str(invoice.id_proyect):
        raise AppError("errors.permission_denied", 403)

    issuer = db.get(CustomerSupplier, invoice.id_issuer_customer_supplier)
    receiver = db.get(CustomerSupplier, invoice.id_customer_supplier)
    if not issuer or not receiver:
        raise AppError("errors.resource_not_found", 404)
    lines = db.scalars(
        select(InvoiceMaterialService).where(
            InvoiceMaterialService.id_invoice == invoice.id_invoice,
            InvoiceMaterialService.authorization_status == "authorized",
            InvoiceMaterialService.deletion_date.is_(None),
        )
    ).all()
    return invoice, build_draft(invoice, issuer, receiver, lines, _related_documents(db, invoice))


def _related_documents(db, invoice) -> list[dict]:
    """Comprobantes con los que este se relaciona, para el nodo CfdiRelacionados.

    Las relaciones ya se guardaban en `cfdi_relation`, pero no llegaban al XML:
    una nota de credito se timbraba como un egreso suelto, sin decirle al SAT
    que factura corrige. Ante la autoridad esa nota no reducia nada, y el enlace
    solo existia dentro del sistema.
    """
    from app.models.cfdi_relation import CfdiRelation

    # La tabla no lleva borrado logico: una relacion fiscal ya timbrada no se
    # deshace borrandola, se corrige con otro comprobante.
    relaciones = db.scalars(
        select(CfdiRelation)
        .where(CfdiRelation.id_invoice == invoice.id_invoice)
        .order_by(CfdiRelation.id_cfdi_relation)
    ).all()
    return [
        {"relation_type": relacion.relation_type, "uuid": relacion.related_uuid}
        for relacion in relaciones
        if str(relacion.related_uuid or "").strip()
    ]


def preflight_invoice(invoice_id, user_data) -> dict:
    """Revisa si una factura es timbrable, sin llamar al PAC.

    Devuelve los errores que impiden timbrar, las advertencias a revisar, los
    totales calculados con las reglas del SAT y el XML que se generaria. Sirve
    para que operaciones detecte los problemas antes de consumir un timbre.
    """
    with transaction_context() as db:
        invoice, draft = _load_draft(db, invoice_id, user_data)
        review = inspect_draft(draft)
        payload = draft.serialize()
        preview_xml = None
        document_errors: list[str] = []
        if not review["errors"]:
            _, preview_xml = build_fake_cfdi_xml(payload)
            document_errors = validate_cfdi_xml(preview_xml)
        # El total guardado en la cabecera puede quedar obsoleto si se editaron
        # partidas despues de capturarla. No impide timbrar (el CFDI se arma de
        # las partidas y `stamp_invoice` reescribe los importes con los del
        # comprobante), pero conviene avisarlo antes de gastar un timbre.
        stored_total = Decimal(str(invoice.total or 0))
        computed_total = Decimal(payload["totals"]["total"])
        drift = [] if stored_total == computed_total else ["invoice.stored_total_differs_from_cfdi_total"]
        return {
            "id_invoice": invoice.id_invoice,
            "can_stamp": not (review["errors"] or document_errors),
            "errors": review["errors"] + document_errors,
            "warnings": review["warnings"] + drift,
            "totals": payload["totals"],
            "stored_total": format(stored_total, "f"),
            "authorized_lines": len(draft.concepts),
            "preview_xml": preview_xml,
        }


NO_SE_TIMBRA = {"timbrada", "cancelada", "pagada", "draft", "sent", "approved",
                "partially_approved", "rejected", "cotizacion", "cotización"}


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

        pending_invoice = db.get(Invoice, invoice_id)
        if not pending_invoice:
            raise AppError("errors.resource_not_found", 404)
        # Timbrar de nuevo con otra llave de idempotencia generaba un segundo UUID
        # sobre la misma factura (y revivia una cancelada). Una factura ya
        # timbrada o cancelada no se timbra otra vez, y una cotizacion que no se
        # ha convertido todavia no es una factura.
        estatus = str(pending_invoice.invoice_status or "").strip().lower()
        if pending_invoice.folio_fiscal or estatus in NO_SE_TIMBRA:
            raise AppError("errors.invoice_not_stampable", 409,
                           {"id_invoice": pending_invoice.id_invoice, "status": estatus})
        next_folio_if_missing(db, pending_invoice)

        invoice, draft = _load_draft(db, invoice_id, user_data)
        review = inspect_draft(draft)
        if review["errors"]:
            raise AppError(
                "invoice.stamping_validation_failed",
                400,
                {"errors": review["errors"], "warnings": review["warnings"]},
            )

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
                xml_bytes = result.xml.encode("utf-8") if isinstance(result.xml, str) else result.xml
                fiscal_data = parse_cfdi(xml_bytes)
                if fiscal_data["uuid"] != str(result.reference).upper():
                    raise AppError("invoice.stamping_uuid_mismatch", 502)
                # Auditamos el comprobante que devuelve el PAC antes de darlo
                # por bueno: si no cumple el Anexo 20 no debe quedar como
                # timbrado en el sistema.
                document_errors = validate_cfdi_xml(xml_bytes)
                if document_errors:
                    operation.status = "rejected"
                    operation.error_code = "cfdi_document_invalid"
                    operation.response_metadata = {**(result.metadata or {}), "cfdi_errors": document_errors}
                    raise AppError("invoice.stamped_document_invalid", 502, {"errors": document_errors})
                save_cfdi_xml(db, invoice.id_invoice, result.xml)
                invoice.cfdi_code = fiscal_data["uuid"]
                invoice.no_certificado = fiscal_data.get("no_certificado")
                invoice.no_certificado_sat = fiscal_data.get("no_certificado_sat")
                invoice.sello_sat = fiscal_data.get("sello_sat")
                # Los importes definitivos son los del comprobante timbrado.
                invoice.subtotal = Decimal(fiscal_data["subtotal"])
                invoice.total = Decimal(fiscal_data["total"])
                certified_at = fiscal_data.get("certification_date")
                if certified_at:
                    invoice.certification_date = datetime.fromisoformat(certified_at).replace(tzinfo=None)
        db.flush()
        return operation.serialize(), True
