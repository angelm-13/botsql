from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from decimal import Decimal, InvalidOperation


MAX_STATEMENT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = {"date", "description", "debit", "credit"}


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
        movements.append({"movement_date": movement_date, "description": description[:500], "debit": debit, "credit": credit})
    if not movements:
        raise ValueError("Statement has no movements")
    return {
        "file_hash": hashlib.sha256(file_bytes).hexdigest(),
        "movements": movements,
        "period_start": min(item["movement_date"] for item in movements),
        "period_end": max(item["movement_date"] for item in movements),
        "total_debits": sum((item["debit"] for item in movements), Decimal("0")),
        "total_credits": sum((item["credit"] for item in movements), Decimal("0")),
    }