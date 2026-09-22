from app.models import Field
from app.services.base_service import CrudService


class FieldService(CrudService):
    model = Field
    primary_key = 'id_field'
    entity_name = 'field'

    # Un campo de baja es una columna que ya no existe en la tabla, o una que
    # el sistema administra solo (`created_by` y las tres fechas). El sembrado
    # las retira; ofrecerlas en el gestor es pedir que alguien decida si un rol
    # ve una columna que no se puede ver.
    solo_vigentes = True
