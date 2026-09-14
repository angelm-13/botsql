from decimal import Decimal, InvalidOperation

from app.models import CustomerSupplier, LogisticsInventory, LogisticsLocation
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsInventoryService(CrudService):
    model = LogisticsInventory
    primary_key = 'id_logistics_inventory'
    entity_name = 'logistics_inventory'

    @classmethod
    def _validate(cls, payload: dict, *, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._validate_fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', creating)
        cls._validate_fk(payload, 'id_logistics_location', LogisticsLocation, 'location', creating)
        if 'quantity' in payload and payload['quantity'] not in (None, ''):
            try:
                if Decimal(str(payload['quantity'])) < 0:
                    raise AppError('validations.logistics_inventory.quantity.invalid', status_code=400, meta={'field': 'quantity'})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': 'quantity'})
        if 'status' in payload and payload['status'] not in {'activo', 'pendiente_surtido', 'surtido', 'inactivo'}:
            raise AppError('validations.logistics_inventory.status.invalid', status_code=400, meta={'field': 'status'})
        return payload

    @staticmethod
    def _validate_fk(payload: dict, field: str, model, label: str, creating: bool) -> None:
        value = payload.get(field)
        if value in (None, ''):
            if creating:
                raise AppError(f'validations.logistics_inventory.{label}.required', status_code=400, meta={'field': field})
            return
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise AppError(f'validations.logistics_inventory.{label}.invalid', status_code=400, meta={'field': field})
        with transaction_context() as session:
            item = session.get(model, value)
            if not item or item.deletion_date is not None or (label == 'client' and item.type != 'client'):
                raise AppError(f'validations.logistics_inventory.{label}.invalid', status_code=400, meta={'field': field})
        payload[field] = value

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None, user_data: dict | None = None):
        creado = super().create(cls._validate(payload, creating=True), user_id=user_id)
        # Un alta parte de cero: la diferencia es la cantidad entera.
        cls._reflejar(creado, Decimal("0"), user_id, "Entrada de mercancia en custodia",
                      user_data=user_data)
        return creado

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None,
               user_data: dict | None = None):
        # El saldo ANTERIOR, antes de que el CRUD lo sobrescriba. Esta tabla no
        # lleva libro -- cada edicion pisa `quantity` sin rastro -- asi que sin
        # leerlo aqui no hay forma de saber cuanto entro o salio.
        anterior = cls._saldo_actual(item_id)
        actualizado = super().update(item_id, cls._validate(payload), user_id=user_id)
        cls._reflejar(actualizado, anterior, user_id,
                      "Movimiento de mercancia en custodia", user_data=user_data)
        return actualizado

    @classmethod
    def _saldo_actual(cls, item_id) -> Decimal:
        with transaction_context() as db:
            fila = db.get(LogisticsInventory, int(item_id))
            return Decimal(str(getattr(fila, "quantity", 0) or 0)) if fila else Decimal("0")

    @classmethod
    def _reflejar(cls, resultado, anterior, user_id, motivo, *, user_data=None) -> None:
        """Anota la diferencia en el libro del nucleo, si la fila esta enlazada.

        Un solo inventario para todos los proyectos: ver
        `logistics_inventory_bridge`. Nunca lanza -- la mercancia ya entro o
        salio del estante, y revertir el registro por un problema de anotacion
        dejaria la fila mintiendo sobre lo que hay.

        El puente se importa aqui y no arriba porque arrastra los modelos del
        nucleo, y este modulo se carga al registrar los blueprints.
        """
        from app.services.logistics_inventory_bridge import reflejar_cambio

        id_fila = (resultado or {}).get("id_logistics_inventory")
        if not id_fila:
            return
        with transaction_context() as db:
            fila = db.get(LogisticsInventory, int(id_fila))
            if fila is None or not getattr(fila, "id_product", None):
                return
            # El `user_data` ENTERO y no solo el id: el nucleo comprueba que
            # el proyecto del actor coincida con el del movimiento, y ese
            # proyecto viene en el token. Con solo el id, todo reflejo moria
            # con `errors.permission_denied` -- medido.
            actor = dict(user_data or {})
            actor.setdefault("id_user", user_id or 1)
            reflejar_cambio(db, fila, anterior, actor, motivo=motivo)