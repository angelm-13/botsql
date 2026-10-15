from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func, text
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


class InvoiceMaterialService(Base):
    __tablename__ = 'invoice_material_service'

    id_invoice_material_service: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_invoice: Mapped[int] = mapped_column(Integer, ForeignKey('invoice.id_invoice'), nullable=False)
    id_material: Mapped[int] = mapped_column(Integer, ForeignKey('material.id_material'), nullable=True)
    id_service: Mapped[int] = mapped_column(Integer, ForeignKey('service.id_service'), nullable=True)
    invoice_material_service_description: Mapped[object] = mapped_column(String(200), nullable=False)
    max_requirement_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    is_directly_related_to_product_service_creation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    id_authorized: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    id_status: Mapped[int] = mapped_column(Integer, ForeignKey('status.id_status'), nullable=False)
    id_buyer: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    gross_price: Mapped[float] = mapped_column(Numeric(18,6), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18,6), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey('product.id_product'), nullable=True)
    line_type: Mapped[object] = mapped_column(Enum('product', 'service', 'custom', name='invoice_material_service_line_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    tax_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    line_tax: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    line_total: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    id_unit: Mapped[int] = mapped_column(Integer, ForeignKey('unit.id_unit'), nullable=True)
    authorization_status: Mapped[object] = mapped_column(Enum('pending', 'authorized', 'rejected', name='invoice_material_service_authorization_status_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    authorization_note: Mapped[object] = mapped_column(String(500), nullable=True)
    authorization_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    id_task: Mapped[int] = mapped_column(Integer, ForeignKey('task.id_task'), nullable=True)
    discount: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    sat_product_key: Mapped[object] = mapped_column(String(20), nullable=True)
    sat_unit_key: Mapped[object] = mapped_column(String(10), nullable=True)
    tax_object: Mapped[object] = mapped_column(String(5), nullable=True)
    tax_rate: Mapped[float] = mapped_column(Numeric(9,6), nullable=True)
    isr_retention_rate: Mapped[float] = mapped_column(Numeric(9,6), nullable=True)
    iva_retention_rate: Mapped[float] = mapped_column(Numeric(9,6), nullable=True)
    # IVA exento (TipoFactor="Exento" en el CFDI): el SAT lo distingue de la
    # tasa 0%, que si lleva TasaOCuota e Importe en el nodo Traslado.
    iva_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'), default=False)
    # De que renglon original viene esta partida, cuando el renglon es de una
    # nota de credito que acredita una cantidad puntual de un producto ya
    # facturado. Nulo para lo que no corresponde a un renglon original -una
    # bonificacion global, por ejemplo-. Ver invoice_credit_note_service.py.
    id_original_line: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('invoice_material_service.id_invoice_material_service'), nullable=True)

    def serialize(self) -> dict:
        return {
            'id_invoice_material_service': to_json_value(self.id_invoice_material_service),
            'id_invoice': to_json_value(self.id_invoice),
            'id_material': to_json_value(self.id_material),
            'id_service': to_json_value(self.id_service),
            'invoice_material_service_description': to_json_value(self.invoice_material_service_description),
            'max_requirement_date': to_json_value(self.max_requirement_date),
            'is_directly_related_to_product_service_creation': to_json_value(self.is_directly_related_to_product_service_creation),
            'id_authorized': to_json_value(self.id_authorized),
            'id_status': to_json_value(self.id_status),
            'id_buyer': to_json_value(self.id_buyer),
            'id_customer_supplier': to_json_value(self.id_customer_supplier),
            'gross_price': to_json_value(self.gross_price),
            'quantity': to_json_value(self.quantity),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
            'id_product': to_json_value(self.id_product),
            'line_type': to_json_value(self.line_type),
            'tax_applicable': to_json_value(self.tax_applicable),
            'line_tax': to_json_value(self.line_tax),
            'line_total': to_json_value(self.line_total),
            'id_unit': to_json_value(self.id_unit),
            'authorization_status': to_json_value(self.authorization_status),
            'authorization_note': to_json_value(self.authorization_note),
            'authorization_date': to_json_value(self.authorization_date),
            'id_task': to_json_value(self.id_task),
            'discount': to_json_value(self.discount),
            'sat_product_key': to_json_value(self.sat_product_key),
            'sat_unit_key': to_json_value(self.sat_unit_key),
            'tax_object': to_json_value(self.tax_object),
            'tax_rate': to_json_value(self.tax_rate),
            'isr_retention_rate': to_json_value(self.isr_retention_rate),
            'iva_retention_rate': to_json_value(self.iva_retention_rate),
            'iva_exempt': to_json_value(self.iva_exempt),
            'id_original_line': to_json_value(self.id_original_line),
        }

    def serialize_summary(self) -> dict:
        return {'id_invoice_material_service': self.id_invoice_material_service}
