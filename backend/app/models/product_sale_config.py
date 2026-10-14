from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base
from app.utils.tiempo import a_iso_utc


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class ProductSaleConfig(Base):
    __tablename__ = 'product_sale_config'

    id_product_sale_config: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey('product.id_product'), nullable=False)
    margin_percent: Mapped[float] = mapped_column(Numeric(5,2), nullable=True)
    manual_price: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    id_inventory_status: Mapped[int] = mapped_column(Integer, ForeignKey('inventory_status.id_inventory_status'), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_product_sale_config': to_json_value(self.id_product_sale_config),
            'id_product': to_json_value(self.id_product),
            'margin_percent': to_json_value(self.margin_percent),
            'manual_price': to_json_value(self.manual_price),
            'id_inventory_status': to_json_value(self.id_inventory_status),
            'is_active': to_json_value(self.is_active),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_product_sale_config': self.id_product_sale_config}
