from app.models import NmFieldPermission
from app.services.base_service import CrudService


class NmFieldPermissionService(CrudService):
    model = NmFieldPermission
    primary_key = 'id_nm_field_permission'
    entity_name = 'nm_field_permission'

    # De estas filas salen los atributos que una pantalla pinta. Una de baja
    # significa que el permiso se retiro, asi que devolverla vuelve a mostrar
    # el campo: el listado la escondia y la pantalla la creia concedida.
    solo_vigentes = True
