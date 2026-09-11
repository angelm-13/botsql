"""Las parcialidades de pago de un proyecto.

Por que una tabla y no columnas
-------------------------------
Un proyecto de taller se cobra en varios pagos -- "40% al pedir, 60% contra
entrega" -- y cada uno tiene su fecha, su monto y el porcentaje acordado. Tres
columnas en `proyect` alcanzarian para un pago; para dos harian falta seis, y
para tres, nueve. Una fila por pago es lo unico que no se queda corto.

El porcentaje se guarda, no se deduce
-------------------------------------
Lo que se acuerda con el cliente es "40% al pedir". Si despues cambia el total
del proyecto -- se amplia el alcance, se ajusta la cotizacion --, ese 40%
pactado sigue siendo el que se firmo. Calcularlo hoy como `monto / total`
reescribiria el acuerdo cada vez que el total se mueva.

Lo acordado y lo cobrado son dos hechos
---------------------------------------
`payment_date` es cuando se acordo o se espera; `paid_at`, cuando entro de
verdad. Un pago que cae dos semanas tarde sigue siendo el pago acordado para su
fecha, y mezclar las dos en una columna borra el retraso -- que es justo lo que
alguien quiere ver.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, Text, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _valor(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class ProyectPayment(Base):
    __tablename__ = "proyect_payment"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_proyect_payment_amount"),
        CheckConstraint(
            "agreed_percent IS NULL OR (agreed_percent > 0 AND agreed_percent <= 100)",
            name="ck_proyect_payment_percent",
        ),
    )

    id_proyect_payment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(
        Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    agreed_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {c.name: _valor(getattr(self, c.name)) for c in self.__table__.columns}
