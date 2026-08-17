from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Invoice(Base):
    __tablename__ = 'invoice'

    id_invoice: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    date_emision: Mapped[object] = mapped_column(DateTime, nullable=True)
    date_expiration: Mapped[object] = mapped_column(DateTime, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    tax: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    invoice_status: Mapped[object] = mapped_column(String(20), nullable=True)
    payment_method: Mapped[object] = mapped_column(String(50), nullable=True)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    fiscal_reference: Mapped[object] = mapped_column(String(50), nullable=True)
    serie_csd: Mapped[object] = mapped_column(String(150), nullable=True)
    internationalization: Mapped[object] = mapped_column(Enum('exported', 'imported', 'local', name='invoice_internationalization_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    currency: Mapped[object] = mapped_column(String(30), nullable=True)
    type_exchange_rate: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    tax_certification_supplier: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_certify_serie: Mapped[object] = mapped_column(String(150), nullable=True)
    certification_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    cfdi_code: Mapped[object] = mapped_column(String(500), nullable=True)
    sat_code: Mapped[object] = mapped_column(String(500), nullable=True)
    sat_certification_code: Mapped[object] = mapped_column(String(500), nullable=True)
    id_status: Mapped[int] = mapped_column(Integer, ForeignKey('status.id_status'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    nombre_emisor: Mapped[object] = mapped_column(String(150), nullable=True)
    lugar_expedicion: Mapped[object] = mapped_column(String(120), nullable=True)
    tipo_de_comprobante: Mapped[object] = mapped_column(String(50), nullable=True)
    rfc_receptor: Mapped[object] = mapped_column(String(20), nullable=True)
    nombre_receptor: Mapped[object] = mapped_column(String(150), nullable=True)
    regimen_fiscal_receptor: Mapped[object] = mapped_column(String(100), nullable=True)
    domicilio_fiscal_receptor: Mapped[object] = mapped_column(String(250), nullable=True)
    id_proveedor_de_sello: Mapped[int] = mapped_column(Integer, nullable=True)
    folio_fiscal: Mapped[object] = mapped_column(String(50), nullable=True)
    exportacion: Mapped[object] = mapped_column(String(50), nullable=True)
    folio: Mapped[object] = mapped_column(String(30), nullable=True)
    no_certificado_sat: Mapped[object] = mapped_column(String(50), nullable=True)
    sello_sat: Mapped[object] = mapped_column(String(500), nullable=True)
    sello_certificacion_sat: Mapped[object] = mapped_column(String(500), nullable=True)
    no_certificado: Mapped[object] = mapped_column(String(50), nullable=True)
    descuento: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    metodo_pago: Mapped[object] = mapped_column(String(50), nullable=True)
    condiciones_pago: Mapped[object] = mapped_column(String(100), nullable=True)
    id_issuer_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True)
    apply_tax: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(5,2), nullable=True)
    commercial_terms: Mapped[object] = mapped_column(String(500), nullable=True)

    def serialize(self) -> dict:
        return {
            'id_invoice': to_json_value(self.id_invoice),
            'date_emision': to_json_value(self.date_emision),
            'date_expiration': to_json_value(self.date_expiration),
            'subtotal': to_json_value(self.subtotal),
            'tax': to_json_value(self.tax),
            'total': to_json_value(self.total),
            'invoice_status': to_json_value(self.invoice_status),
            'payment_method': to_json_value(self.payment_method),
            'note': to_json_value(self.note),
            'id_customer_supplier': to_json_value(self.id_customer_supplier),
            'fiscal_reference': to_json_value(self.fiscal_reference),
            'serie_csd': to_json_value(self.serie_csd),
            'internationalization': to_json_value(self.internationalization),
            'currency': to_json_value(self.currency),
            'type_exchange_rate': to_json_value(self.type_exchange_rate),
            'tax_certification_supplier': to_json_value(self.tax_certification_supplier),
            'fiscal_certify_serie': to_json_value(self.fiscal_certify_serie),
            'certification_date': to_json_value(self.certification_date),
            'cfdi_code': to_json_value(self.cfdi_code),
            'sat_code': to_json_value(self.sat_code),
            'sat_certification_code': to_json_value(self.sat_certification_code),
            'id_status': to_json_value(self.id_status),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
            'nombre_emisor': to_json_value(self.nombre_emisor),
            'lugar_expedicion': to_json_value(self.lugar_expedicion),
            'tipo_de_comprobante': to_json_value(self.tipo_de_comprobante),
            'rfc_receptor': to_json_value(self.rfc_receptor),
            'nombre_receptor': to_json_value(self.nombre_receptor),
            'regimen_fiscal_receptor': to_json_value(self.regimen_fiscal_receptor),
            'domicilio_fiscal_receptor': to_json_value(self.domicilio_fiscal_receptor),
            'id_proveedor_de_sello': to_json_value(self.id_proveedor_de_sello),
            'folio_fiscal': to_json_value(self.folio_fiscal),
            'exportacion': to_json_value(self.exportacion),
            'folio': to_json_value(self.folio),
            'no_certificado_sat': to_json_value(self.no_certificado_sat),
            'sello_sat': to_json_value(self.sello_sat),
            'sello_certificacion_sat': to_json_value(self.sello_certificacion_sat),
            'no_certificado': to_json_value(self.no_certificado),
            'descuento': to_json_value(self.descuento),
            'metodo_pago': to_json_value(self.metodo_pago),
            'condiciones_pago': to_json_value(self.condiciones_pago),
            'id_issuer_customer_supplier': to_json_value(self.id_issuer_customer_supplier),
            'id_proyect': to_json_value(self.id_proyect),
            'apply_tax': to_json_value(self.apply_tax),
            'tax_rate': to_json_value(self.tax_rate),
            'commercial_terms': to_json_value(self.commercial_terms),
        }

    def serialize_summary(self) -> dict:
        return {'id_invoice': self.id_invoice}
