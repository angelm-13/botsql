from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class BankStatement(Base):
    __tablename__ = "bank_statement"
    __table_args__ = (UniqueConstraint("file_hash", name="uq_bank_statement_file_hash"),)

    id_bank_statement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_bank_account: Mapped[int] = mapped_column(ForeignKey("bank_account.id_bank_account"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(ForeignKey("proyect.id_proyect"), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    starting_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ending_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    average_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    extraction_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reconciliation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            "id_bank_statement": self.id_bank_statement,
            "id_bank_account": self.id_bank_account,
            "id_proyect": self.id_proyect,
            "file_hash": self.file_hash,
            "original_filename": self.original_filename,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_debits": float(self.total_debits or 0),
            "total_credits": float(self.total_credits or 0),
            "status": self.status,
            "starting_balance": float(self.starting_balance) if self.starting_balance is not None else None,
            "ending_balance": float(self.ending_balance) if self.ending_balance is not None else None,
            "average_balance": float(self.average_balance) if self.average_balance is not None else None,
            "parser_name": self.parser_name,
            "extraction_confidence": float(self.extraction_confidence) if self.extraction_confidence is not None else None,
            "extraction_errors": self.extraction_errors or [],
            "reconciliation_data": self.reconciliation_data or {},
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
        }


class BankStatementMovement(Base):
    __tablename__ = "bank_statement_movement"
    __table_args__ = (UniqueConstraint("id_bank_statement", "sequence_number", name="uq_bank_statement_movement_row"),)

    id_bank_statement_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_bank_statement: Mapped[int] = mapped_column(ForeignKey("bank_statement.id_bank_statement"), nullable=False, index=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin_bank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    beneficiary: Mapped[str | None] = mapped_column(String(200), nullable=True)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_invoice: Mapped[int | None] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=True)

    def serialize(self) -> dict:
        return {
            "id_bank_statement_movement": self.id_bank_statement_movement,
            "id_bank_statement": self.id_bank_statement,
            "movement_date": self.movement_date.isoformat() if self.movement_date else None,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "description": self.description,
            "debit": float(self.debit or 0),
            "credit": float(self.credit or 0),
            "sequence_number": self.sequence_number,
            "code": self.code,
            "reference": self.reference,
            "order_number": self.order_number,
            "origin_bank": self.origin_bank,
            "origin_account": self.origin_account,
            "beneficiary": self.beneficiary,
            "balance": float(self.balance) if self.balance is not None else None,
            "id_invoice": self.id_invoice,
            "reconciliation_note": self.reconciliation_note,
        }