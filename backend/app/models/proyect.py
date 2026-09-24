from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func, text
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Proyect(Base):
    __tablename__ = 'proyect'

    id_proyect: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    # El contacto elegido (empresa+persona fusionados); de aqui se derivan
    # `id_customer_supplier` y `requested_by` al guardar. Ver
    # 20260921100000_contactos_por_empresa_y_adjuntos_del_proyecto.
    id_customer_contact: Mapped[int | None] = mapped_column(Integer, ForeignKey('customer_contact.id_customer_contact'), nullable=True)
    leader: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    proyect_description: Mapped[object] = mapped_column(String(200), nullable=False)
    title: Mapped[object] = mapped_column(String(50), nullable=True)
    # El recorrido del TALLER. Ver PROJECT_STATUSES en project_management_service.
    proyect_status: Mapped[object] = mapped_column(String(20), nullable=False, default='draft', server_default=text("'draft'"))
    # --- la orden de trabajo (migracion 20260911180000) ---
    folio: Mapped[object] = mapped_column(String(40), nullable=True)
    # Quien lo pidio: una empresa tiene varios ingenieros pidiendo cosas
    # distintas, y `id_customer_supplier` solo dice la empresa.
    requested_by: Mapped[object] = mapped_column(String(160), nullable=True)
    # La cotizacion de la que salio; en TYAKXA es una `invoice` en su primer momento.
    id_quotation: Mapped[int] = mapped_column(Integer, ForeignKey('invoice.id_invoice'), nullable=True)
    # Folio de un sistema de cotizacion EXTERNO (ej. adser, obligado por su
    # proveedor a cotizar fuera de tyakxa_tny): nunca genera una fila de
    # `invoice` aqui. Se llena solo cuando `id_quotation` no aplica -- las dos
    # nunca coexisten en el mismo proyecto.
    quotation_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Numeros del documento del CLIENTE, no de los nuestros.
    purchase_order: Mapped[object] = mapped_column(String(60), nullable=True)
    purchase_order_item: Mapped[int] = mapped_column(Integer, nullable=True)
    # El supervisor manda en el piso; el `leader` responde ante el cliente.
    id_supervisor: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=True)
    delivery_date: Mapped[object] = mapped_column(Date, nullable=True)
    # El plano o la foto, como `document`: asi conserva version, sha256 y tipo.
    id_drawing_document: Mapped[int] = mapped_column(Integer, ForeignKey('document.id_document'), nullable=True)
    # La vida COMERCIAL, que corre en paralelo a la de taller: un proyecto puede
    # estar entregado y sin cobrar, y eso una sola columna no lo puede decir.
    management_status: Mapped[object] = mapped_column(
        String(40), nullable=True, default='pendiente_orden_compra',
        server_default=text("'pendiente_orden_compra'"))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_proyect': to_json_value(self.id_proyect),
            'id_customer_supplier': to_json_value(self.id_customer_supplier),
            'id_customer_contact': to_json_value(self.id_customer_contact),
            'leader': to_json_value(self.leader),
            'proyect_description': to_json_value(self.proyect_description),
            'title': to_json_value(self.title),
            'proyect_status': to_json_value(self.proyect_status),
            'management_status': to_json_value(self.management_status),
            'id_drawing_document': to_json_value(self.id_drawing_document),
            'delivery_date': to_json_value(self.delivery_date),
            'id_supervisor': to_json_value(self.id_supervisor),
            'purchase_order_item': to_json_value(self.purchase_order_item),
            'purchase_order': to_json_value(self.purchase_order),
            'id_quotation': to_json_value(self.id_quotation),
            'quotation_reference': to_json_value(self.quotation_reference),
            'requested_by': to_json_value(self.requested_by),
            'folio': to_json_value(self.folio),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_proyect': self.id_proyect}
