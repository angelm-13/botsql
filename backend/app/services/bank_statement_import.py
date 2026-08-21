from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation


MAX_STATEMENT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = {"date", "description", "debit", "credit"}
MONTHS = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
AMOUNT_RE = re.compile(r"[-+]?\$?\s*[\d,]+\.\d{2}")


def _amount(value, field):
    text = str(value or "").strip().replace(",", "") or "0"
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {field} amount") from exc
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return amount.quantize(Decimal("0.01"))


def parse_statement_csv(file_bytes, max_bytes=MAX_STATEMENT_BYTES):
    if not file_bytes or len(file_bytes) > max_bytes:
        raise ValueError("Statement file is empty or exceeds size limit")
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Statement must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(text))
    columns = {str(name or "").strip().lower() for name in (reader.fieldnames or [])}
    if not REQUIRED_COLUMNS.issubset(columns):
        raise ValueError("Statement requires date, description, debit and credit columns")

    movements = []
    for line_number, raw in enumerate(reader, start=2):
        row = {str(key).strip().lower(): value for key, value in raw.items()}
        try:
            movement_date = date.fromisoformat(str(row["date"] or "").strip())
        except ValueError as exc:
            raise ValueError(f"Invalid date on line {line_number}") from exc
        description = str(row["description"] or "").strip()
        debit = _amount(row["debit"], "debit")
        credit = _amount(row["credit"], "credit")
        if not description or (debit == 0) == (credit == 0):
            raise ValueError(f"Line {line_number} must contain one debit or one credit")
        movements.append({"movement_date": movement_date, "description": description[:500], "debit": debit, "credit": credit, "sequence_number": len(movements) + 1})
    if not movements:
        raise ValueError("Statement has no movements")
    return {
        "file_hash": hashlib.sha256(file_bytes).hexdigest(),
        "movements": movements,
        "period_start": min(item["movement_date"] for item in movements),
        "period_end": max(item["movement_date"] for item in movements),
        "total_debits": sum((item["debit"] for item in movements), Decimal("0")),
        "total_credits": sum((item["credit"] for item in movements), Decimal("0")),
        "parser_name": "csv",
    }


def _clean_amount(value):
    return Decimal(str(value or "0").replace("$", "").replace(",", "").replace(" ", "")).quantize(Decimal("0.01"))


def _spanish_date(value, fallback_year):
    value = str(value or "").strip().upper()
    numeric = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value)
    if numeric:
        return date(int(numeric.group(3)), int(numeric.group(2)), int(numeric.group(1)))
    named = re.fullmatch(r"(\d{2})/([A-Z]{3})(?:/(\d{2,4}))?", value)
    if not named or named.group(2) not in MONTHS:
        return None
    raw_year = named.group(3)
    year = fallback_year if not raw_year else (2000 + int(raw_year) if len(raw_year) == 2 else int(raw_year))
    return date(year, MONTHS[named.group(2)], int(named.group(1)))


def _header_amount(text, label):
    match = re.search(rf"{label}\s*:?[ \t]*([-+]?\$?\s*[\d,]+\.\d{{2}})", text, re.IGNORECASE)
    return _clean_amount(match.group(1)) if match else None


def parse_bbva_text(text, file_bytes=b""):
    period = re.search(r"PERIODO\s+DEL\s+(\d{2}/\d{2}/\d{4})\s+AL\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    period_start = _spanish_date(period.group(1), date.today().year) if period else None
    period_end = _spanish_date(period.group(2), date.today().year) if period else None
    fallback_year = (period_end or period_start or date.today()).year
    movements = []
    row_re = re.compile(r"^\s*(\d{2}/(?:\d{2}/\d{4}|[A-Z]{3}(?:/\d{2,4})?))\s+(\d{2}/(?:\d{2}/\d{4}|[A-Z]{3}(?:/\d{2,4})?))\s+(.*)$", re.IGNORECASE)
    for raw_line in text.splitlines():
        match = row_re.match(raw_line)
        if not match:
            continue
        amounts = list(AMOUNT_RE.finditer(match.group(3)))
        if len(amounts) < 2:
            continue
        description_end = amounts[0].start()
        descriptor = match.group(3)[:description_end].strip()
        descriptor_parts = descriptor.split(maxsplit=1)
        code = descriptor_parts[0][:30] if descriptor_parts else None
        description = descriptor_parts[1] if len(descriptor_parts) > 1 else descriptor
        values = [_clean_amount(item.group(0)) for item in amounts]
        debit, credit = values[0], values[1]
        if (debit > 0) == (credit > 0):
            inferred_credit = any(word in descriptor.upper() for word in ("DEPOSITO", "RECIBIDO", "ABONO", "DEVOLUCION"))
            movement_amount = debit or credit
            debit, credit = (Decimal("0"), movement_amount) if inferred_credit else (movement_amount, Decimal("0"))
        if debit == 0 and credit == 0:
            continue
        movements.append({
            "movement_date": _spanish_date(match.group(1), fallback_year),
            "settlement_date": _spanish_date(match.group(2), fallback_year),
            "description": (description or descriptor or "Movimiento bancario")[:500],
            "debit": debit,
            "credit": credit,
            "balance": values[-1] if len(values) >= 3 else None,
            "code": code,
            "sequence_number": len(movements) + 1,
        })
    if not movements:
        raise ValueError("No se encontraron movimientos en el estado de cuenta BBVA")
    calculated_debits = sum((item["debit"] for item in movements), Decimal("0"))
    calculated_credits = sum((item["credit"] for item in movements), Decimal("0"))
    return {
        "file_hash": hashlib.sha256(file_bytes or text.encode("utf-8")).hexdigest(),
        "movements": movements,
        "period_start": period_start or min(item["movement_date"] for item in movements),
        "period_end": period_end or max(item["movement_date"] for item in movements),
        "total_debits": calculated_debits,
        "total_credits": calculated_credits,
        "document_total_debits": _header_amount(text, r"TOTAL\s+CARGOS"),
        "document_total_credits": _header_amount(text, r"TOTAL\s+ABONOS"),
        "starting_balance": _header_amount(text, r"SALDO\s+INICIAL"),
        "ending_balance": _header_amount(text, r"SALDO\s+FINAL"),
        "average_balance": _header_amount(text, r"SALDO\s+PROMEDIO"),
        "parser_name": "bbva_heuristic_v1",
    }


def reconcile_statement(parsed, tolerance=Decimal("0.05")):
    warnings = []
    differences = {}
    for key, calculated_key, label in (
        ("document_total_debits", "total_debits", "cargos"),
        ("document_total_credits", "total_credits", "abonos"),
    ):
        if parsed.get(key) is None:
            continue
        difference = (parsed[calculated_key] - parsed[key]).quantize(Decimal("0.01"))
        differences[f"difference_{label}"] = float(difference)
        if abs(difference) > tolerance:
            warnings.append(f"La suma de {label} no coincide con el total del documento.")
    if parsed.get("starting_balance") is not None and parsed.get("ending_balance") is not None:
        projected = parsed["starting_balance"] - parsed["total_debits"] + parsed["total_credits"]
        difference = (projected - parsed["ending_balance"]).quantize(Decimal("0.01"))
        differences["difference_ending_balance"] = float(difference)
        if abs(difference) > tolerance:
            warnings.append("El saldo final no coincide con saldo inicial - cargos + abonos.")
    return {"ok": not warnings, "warnings": warnings, "differences": differences, "tolerance": float(tolerance)}


def parse_statement_pdf(file_bytes, max_bytes=10 * 1024 * 1024):
    if not file_bytes or len(file_bytes) > max_bytes or not file_bytes.startswith(b"%PDF-"):
        raise ValueError("El archivo no es un PDF valido o excede el limite permitido")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
    except ImportError as exc:
        raise ValueError("El servidor no tiene disponible el lector PDF") from exc
    except Exception as exc:
        raise ValueError("No se pudo leer el PDF") from exc
    if reader.is_encrypted:
        raise ValueError("El PDF esta cifrado")
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not text.strip():
        raise ValueError("El PDF requiere OCR porque no contiene texto extraible")
    return parse_bbva_text(text, file_bytes=file_bytes)


def parse_bank_statement(file_bytes, filename):
    return parse_statement_pdf(file_bytes) if str(filename or "").lower().endswith(".pdf") else parse_statement_csv(file_bytes)