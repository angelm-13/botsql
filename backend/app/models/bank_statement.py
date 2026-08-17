from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class BankStatementMovement(Base):
    __tablename__ = "bank_statement_movement"

    id_bank_statement_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_bank_statement: Mapped[int] = mapped_column(ForeignKey("bank_statement.id_bank_statement"), nullable=False, index=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    id_invoice: Mapped[int | None] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=True)