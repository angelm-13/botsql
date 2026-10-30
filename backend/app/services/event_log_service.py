from app.models import EventLog
from app.services.base_service import CrudService


class EventLogService(CrudService):
    model = EventLog
    primary_key = 'id_event_log'
    entity_name = 'event_log'
    # Editar o borrar un asiento deja su propio asiento (si no, quien borra una
    # linea de la bitacora borra tambien la prueba). Solo el alta no lo deja: el
    # asiento ya es el rastro de si mismo.
    acciones_sin_asiento = frozenset({'create'})
    # Lo mas reciente primero: es lo que se busca en una bitacora.
    orden_por_omision = '-creation_date'
