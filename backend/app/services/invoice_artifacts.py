from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.cfdi_document import build_cfdi_xml


# Huso horario del centro de Mexico. El SAT exige que Fecha corresponda a la
# hora local del lugar de expedicion, no a UTC.
EXPEDITION_TIMEZONE = timezone(timedelta(hours=-6))

MOCK_CERTIFICATE_NUMBER = "30001000000400000001"
MOCK_SAT_CERTIFICATE_NUMBER = "30001000000400000002"
MOCK_PROVIDER_RFC = "MOCK010101AAA"


def invoice_xml_path(invoice_id, upload_root=None) -> Path:
    root = Path(upload_root or os.getenv("UPLOAD_ROOT") or Path(__file__).resolve().parents[3] / "uploads")
    return root / "cfdi_xml" / f"invoice_{int(invoice_id)}.xml"


def save_invoice_xml(invoice_id, xml_content, upload_root=None) -> Path:
    content = xml_content.encode("utf-8") if isinstance(xml_content, str) else bytes(xml_content)
    path = invoice_xml_path(invoice_id, upload_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".xml.tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(path)
    return path


def _expedition_timestamp() -> str:
    return datetime.now(EXPEDITION_TIMEZONE).replace(microsecond=0, tzinfo=None).isoformat()


def build_fake_cfdi_xml(payload: dict, stamp_uuid=None) -> tuple[str, str]:
    """CFDI 4.0 timbrado por el proveedor local, con estructura valida.

    Los sellos y certificados son ficticios (no hay CSD), pero el resto del
    comprobante cumple el esquema y la aritmetica del Anexo 20, de modo que el
    XML sirve para validar el flujo completo sin depender de un PAC.
    """
    stamp_uuid = str(stamp_uuid or uuid.uuid4()).upper()
    issued_at = _expedition_timestamp()
    digest = stamp_uuid.replace("-", "")
    xml = build_cfdi_xml(
        payload,
        issued_at=issued_at,
        certificate_number=MOCK_CERTIFICATE_NUMBER,
        seal=("MOCKCFD" + digest).ljust(344, "A"),
        stamp={
            "uuid": stamp_uuid,
            "stamped_at": issued_at,
            "provider_rfc": MOCK_PROVIDER_RFC,
            "cfd_seal": ("MOCKCFD" + digest).ljust(344, "A"),
            "sat_certificate_number": MOCK_SAT_CERTIFICATE_NUMBER,
            "sat_seal": ("MOCKSAT" + digest).ljust(344, "B"),
        },
    )
    return stamp_uuid, xml
