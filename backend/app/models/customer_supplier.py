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


class CustomerSupplier(Base):
    __tablename__ = 'customer_supplier'

    id_customer_supplier: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    postal_code: Mapped[object] = mapped_column(String(10), nullable=True)
    name: Mapped[object] = mapped_column(String(150), nullable=False)
    title: Mapped[object] = mapped_column(String(50), nullable=True)
    contact_name: Mapped[object] = mapped_column(String(150), nullable=True)
    phone: Mapped[object] = mapped_column(String(30), nullable=True)
    email: Mapped[object] = mapped_column(String(100), nullable=True)
    web_site: Mapped[object] = mapped_column(String(50), nullable=True)
    street: Mapped[object] = mapped_column(String(100), nullable=True)
    number_ext: Mapped[object] = mapped_column(String(5), nullable=True)
    number_int: Mapped[object] = mapped_column(String(5), nullable=True)
    neighborhood: Mapped[object] = mapped_column(String(50), nullable=True)
    city: Mapped[object] = mapped_column(String(50), nullable=True)
    geographic_state: Mapped[object] = mapped_column(String(20), nullable=True)
    fiscal_type: Mapped[object] = mapped_column(String(150), nullable=True)
    last_fiscal_certification_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    tax_id: Mapped[object] = mapped_column(String(50), nullable=True)
    type: Mapped[object] = mapped_column(Enum('client', 'supplier', name='customer_supplier_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    sla_level: Mapped[str] = mapped_column(String(20), nullable=False, default='standard', server_default='standard')
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    logistics_notes: Mapped[object] = mapped_column(Text, nullable=True)
    is_principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text('false'))
    # Estatus del CSD de este emisor ante el PAC multiemisor. `pac_config` es
    # una sola cuenta compartida (no una fila por empresa), asi que el
    # certificado se registra por RFC aqui, no alla.
    csd_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default='none', server_default='none',
    )
    csd_uploaded_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    # Serie de CFDI por defecto de esta empresa (opcional). Se usa para
    # rellenar el campo "Serie" de una factura manual cuando no se captura
    # una distinta por factura -- ver `create_manual_invoice`.
    serie_csd: Mapped[object] = mapped_column(String(25), nullable=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    path_logo: Mapped[object] = mapped_column(String(150), nullable=True)

    def serialize(self) -> dict:
        return {
            'id_customer_supplier': to_json_value(self.id_customer_supplier),
            'postal_code': to_json_value(self.postal_code),
            'name': to_json_value(self.name),
            'title': to_json_value(self.title),
            'contact_name': to_json_value(self.contact_name),
            'phone': to_json_value(self.phone),
            'email': to_json_value(self.email),
            'web_site': to_json_value(self.web_site),
            'street': to_json_value(self.street),
            'number_ext': to_json_value(self.number_ext),
            'number_int': to_json_value(self.number_int),
            'neighborhood': to_json_value(self.neighborhood),
            'city': to_json_value(self.city),
            'geographic_state': to_json_value(self.geographic_state),
            'fiscal_type': to_json_value(self.fiscal_type),
            'last_fiscal_certification_date': to_json_value(self.last_fiscal_certification_date),
            'tax_id': to_json_value(self.tax_id),
            'type': to_json_value(self.type),
            'sla_level': to_json_value(self.sla_level),
            'credit_limit': to_json_value(self.credit_limit),
            'logistics_notes': to_json_value(self.logistics_notes),
            'is_principal': to_json_value(self.is_principal),
            'csd_status': to_json_value(self.csd_status),
            'csd_uploaded_at': to_json_value(self.csd_uploaded_at),
            'serie_csd': to_json_value(self.serie_csd),
            'id_user': to_json_value(self.id_user),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
            'path_logo': to_json_value(self.path_logo),
        }

    def serialize_summary(self) -> dict:
        return {'id_customer_supplier': self.id_customer_supplier}
