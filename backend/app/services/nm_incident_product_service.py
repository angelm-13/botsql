from sqlalchemy import select

from app.models import NmIncidentProduct
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError

# Lo que hace "el mismo renglon": si todo esto coincide con uno vivo, el
# segundo no es otro prestamo, es el mismo capturado dos veces.
CAMPOS_DEL_MISMO_RENGLON = (
    'id_incident', 'id_product', 'id_inventory_asset', 'quantity', 'direction',
    'note', 'start_date', 'due_date', 'close_date',
    'id_location_from', 'id_location_to',
)


class NmIncidentProductService(CrudService):
    model = NmIncidentProduct
    primary_key = 'id_nm_incident_product'
    entity_name = 'nm_incident_product'

    @classmethod
    def _verificar_que_no_es_captura_doble(cls, datos: dict) -> None:
        """Rechaza un renglon identico, en todo, a uno que ya esta vivo.

        No es una restriccion unica sobre (vale, producto): un empleado que
        vuelve a sacar la misma herramienta en otro momento es historial real
        -en adser, 229 de los 257 grupos repetidos lo eran-. Lo que no tiene
        explicacion es el MISMO renglon, con las mismas fechas, cantidad y
        nota, guardado dos veces: eso fue lo que dejo 62 renglones de mas en
        adser, y por eso la comparacion incluye todo lo que distingue a un
        prestamo de otro. Cualquier diferencia real lo deja pasar.

        Esta es la puerta del CRUD generico. `crear_vale` escribe por su
        cuenta, dentro de una sola transaccion.
        """
        condiciones = [NmIncidentProduct.deletion_date.is_(None)]
        for campo in CAMPOS_DEL_MISMO_RENGLON:
            columna = getattr(NmIncidentProduct, campo)
            valor = datos.get(campo)
            condiciones.append(columna.is_(None) if valor is None else columna == valor)
        with transaction_context() as session:
            existente = session.scalars(
                select(NmIncidentProduct.id_nm_incident_product).where(*condiciones).limit(1)
            ).first()
        if existente is not None:
            raise AppError(
                'errors.nm_incident_product_duplicate', 409,
                {'entity': 'nm_incident_product', 'id_nm_incident_product': existente},
            )

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        datos = dict(payload or {})
        if user_id and 'created_by' not in datos:
            datos['created_by'] = user_id
        cls._verificar_que_no_es_captura_doble(cls._coerce_payload(datos))
        return super().create(payload, user_id)
