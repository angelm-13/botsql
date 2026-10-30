"""Ubicaciones del inventario, organizadas en arbol.

Una ubicacion cuelga de otra (`id_location_reference`), y la raiz de cada
rama es el almacen: la ubicacion cuyo tipo esta marcado como almacen. De ahi
para abajo van zonas, racks y posiciones, tantos niveles como haga falta.

El arbol necesita dos protecciones que antes no existian, porque el servicio
era un CRUD sin validacion:

* Sin guardian de ciclos, dos ubicaciones podian quedar apuntandose entre si
  y cualquier recorrido del arbol se colgaba.
* Una ubicacion con existencia no debe poder borrarse: el inventario quedaria
  apuntando a un lugar que ya no existe.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Location, LocationType
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


# Igual que en inventory_service: red contra datos ciclicos, no un limite.
MAX_DEPTH = 20


class LocationService(CrudService):
    model = Location
    primary_key = 'id_location'
    entity_name = 'location'

    @classmethod
    def options(cls) -> list[dict]:
        """Solo id+descripcion, para poner nombre a una ubicacion en un vale.

        A proposito sin el permiso de lectura de `location` (modulo de
        inventario): quien solo SOLICITA material -Supervisor- no administra
        ubicaciones, pero en su prevale tiene que ver de donde sale lo que pide,
        y sin esto la lista llegaba vacia y el campo se quedaba en "-".
        """
        with transaction_context() as session:
            filas = (
                session.query(Location.id_location, Location.location_description)
                .filter(Location.deletion_date.is_(None))
                .order_by(Location.location_description)
                .all()
            )
            return [
                {'id_location': fila[0], 'location_description': fila[1]}
                for fila in filas
            ]

    @classmethod
    def _validate(cls, payload: dict, *, location_id=None) -> dict:
        payload = dict(payload or {})

        if 'id_location_type' in payload and payload['id_location_type'] not in (None, ''):
            type_id = cls._as_int(payload['id_location_type'], 'id_location_type')
            with transaction_context() as db:
                location_type = db.get(LocationType, type_id)
                if not location_type or location_type.deletion_date is not None:
                    raise AppError(
                        'validations.location.id_location_type.invalid',
                        400,
                        {'field': 'id_location_type'},
                    )
            payload['id_location_type'] = type_id

        if 'id_location_reference' in payload:
            parent = payload['id_location_reference']
            if parent in (None, ''):
                payload['id_location_reference'] = None
            else:
                payload['id_location_reference'] = cls._validate_parent(
                    cls._as_int(parent, 'id_location_reference'), location_id
                )

        return payload

    @staticmethod
    def _as_int(value, field):
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.invalid_field', 400, {'field': field}) from exc

    @classmethod
    def _validate_parent(cls, parent_id, location_id):
        """La ubicacion padre debe existir y no puede estar bajo la hija."""
        if location_id is not None and int(parent_id) == int(location_id):
            raise AppError(
                'validations.location.id_location_reference.self_reference',
                400,
                {'field': 'id_location_reference'},
            )

        with transaction_context() as db:
            parent = db.get(Location, parent_id)
            if not parent or parent.deletion_date is not None:
                raise AppError(
                    'validations.location.id_location_reference.invalid',
                    400,
                    {'field': 'id_location_reference'},
                )
            if location_id is None:
                return parent_id

            # Subir desde el padre propuesto: si aparece la propia ubicacion,
            # el movimiento crearia un ciclo.
            current = parent
            for _ in range(MAX_DEPTH):
                if current is None:
                    return parent_id
                if int(current.id_location) == int(location_id):
                    raise AppError(
                        'validations.location.id_location_reference.cycle',
                        409,
                        {'field': 'id_location_reference', 'id_location': location_id},
                    )
                if current.id_location_reference is None:
                    return parent_id
                current = db.get(Location, current.id_location_reference)
            raise AppError(
                'validations.location.id_location_reference.too_deep',
                409,
                {'field': 'id_location_reference', 'max_depth': MAX_DEPTH},
            )

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload, location_id=item_id), user_id=user_id)

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        with transaction_context() as db:
            stock = int(db.scalar(
                select(func.coalesce(func.sum(InventoryStock.quantity), 0))
                .where(InventoryStock.id_location == int(item_id))
            ) or 0)
            if stock > 0:
                raise AppError(
                    'errors.location_has_stock',
                    409,
                    {'id_location': int(item_id), 'quantity': stock},
                )
            children = db.scalars(
                select(Location.id_location)
                .where(Location.id_location_reference == int(item_id))
                .where(Location.deletion_date.is_(None))
            ).all()
            if children:
                raise AppError(
                    'errors.location_has_children',
                    409,
                    {'id_location': int(item_id), 'children': list(children)},
                )
        return super().delete(item_id, user_id=user_id)


def location_tree(user_data=None) -> dict:
    """Arbol de ubicaciones agrupado por almacen, para poblar los selectores."""
    with transaction_context() as db:
        locations = db.scalars(
            select(Location).where(Location.deletion_date.is_(None)).order_by(Location.id_location)
        ).all()
        types = {row.id_location_type: row for row in db.scalars(select(LocationType)).all()}
        stock = {
            row[0]: int(row[1] or 0)
            for row in db.execute(
                select(InventoryStock.id_location, func.sum(InventoryStock.quantity))
                .group_by(InventoryStock.id_location)
            ).all()
        }

        nodes = {
            location.id_location: {
                'id_location': location.id_location,
                'location_description': location.location_description,
                'id_location_type': location.id_location_type,
                'location_type_description': getattr(
                    types.get(location.id_location_type), 'location_type_description', None
                ),
                'is_warehouse': bool(getattr(types.get(location.id_location_type), 'is_warehouse', False)),
                'id_location_reference': location.id_location_reference,
                'quantity': stock.get(location.id_location, 0),
                'children': [],
            }
            for location in locations
        }

        roots = []
        for node in nodes.values():
            parent = nodes.get(node['id_location_reference'])
            # Un padre ausente o borrado deja al nodo como raiz, en lugar de
            # desaparecer de la respuesta.
            (parent['children'] if parent else roots).append(node)

        def rolled_up(node):
            node['children'] = [rolled_up(child) for child in node['children']]
            node['total_quantity'] = node['quantity'] + sum(
                child['total_quantity'] for child in node['children']
            )
            return node

        tree = [rolled_up(root) for root in roots]
        return {
            'items': tree,
            'warehouses': [node for node in tree if node['is_warehouse']],
            'total': len(locations),
        }
