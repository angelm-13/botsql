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


class NmIncidentProduct(Base):
    __tablename__ = 'nm_incident_product'

    id_nm_incident_product: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_incident: Mapped[int] = mapped_column(Integer, ForeignKey('incident.id_incident'), nullable=False)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey('product.id_product'), nullable=False)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    # El renglon tal como venia del sistema anterior. Sin esto, repetir la carga
    # de ~2 787 renglones no podria saber cuales ya estaban.
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Que pieza concreta, cuando el material se rastrea una por una.
    #
    # Nulo para lo fungible: nadie etiqueta trescientos tornillos, y ahi el
    # renglon dice cantidad. Para la herramienta si hace falta, porque devolver
    # "un desarmador" no cierra el prestamo del desarmador que se llevaron.
    #
    # Si hay pieza, la cantidad es 1: lo garantiza un CHECK en la base
    # (ck_nm_incident_product_pieza_es_una).
    id_inventory_asset: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('inventory_asset.id_inventory_asset'), nullable=True)
    # De donde sale y donde queda alojado. El destino puede ser nulo: un vale
    # que entrega herramienta a una persona no la deja en un sitio.
    id_location_from: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('location.id_location'), nullable=True)
    id_location_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('location.id_location'), nullable=True)
    # Que le pasa a la existencia: `salida`, `entrada` o `traslado`. Es el dato
    # que el libro de inventario necesita para saber si descontar, devolver o
    # solo cambiar de sitio.
    direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # A que operador u otro supervisor se le entrega esta pieza -- distinto
    # del responsable del vale completo (`incident.id_user`): el vale puede
    # salir a nombre de un supervisor y la herramienta pasar de mano en mano
    # hasta quien de verdad la va a usar. `custody_confirmed_date` es cuando
    # el supervisor dueño del vale confirma que la recupero de manos de esa
    # persona -- un paso INTERMEDIO, no la devolucion al almacen (esa sigue
    # siendo `close_date`). Ver `warehouse_voucher_service.py`.
    id_user_delivered_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('user.id_user'), nullable=True)
    custody_confirmed_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    # Cuando se avisó por última vez (campanita) que este renglón ya debió
    # volver y no ha vuelto. Deduplica el job periódico que revisa vales
    # vencidos -- sin esto, cada corrida repetiría el mismo aviso.
    overdue_notified_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    # Desde cuando y hasta cuando. `close_date` ya decia cuando se cerro, pero
    # sin `due_date` no se podia listar lo vencido, que es la razon de llevar
    # vales.
    start_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    close_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_nm_incident_product': to_json_value(self.id_nm_incident_product),
            'id_incident': to_json_value(self.id_incident),
            'id_product': to_json_value(self.id_product),
            'note': to_json_value(self.note),
            'quantity': to_json_value(self.quantity),
            'id_inventory_asset': to_json_value(self.id_inventory_asset),
            'id_location_from': to_json_value(self.id_location_from),
            'id_location_to': to_json_value(self.id_location_to),
            'direction': to_json_value(self.direction),
            'id_user_delivered_to': to_json_value(self.id_user_delivered_to),
            'custody_confirmed_date': to_json_value(self.custody_confirmed_date),
            'overdue_notified_date': to_json_value(self.overdue_notified_date),
            'start_date': to_json_value(self.start_date),
            'due_date': to_json_value(self.due_date),
            'close_date': to_json_value(self.close_date),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_incident_product': self.id_nm_incident_product}
