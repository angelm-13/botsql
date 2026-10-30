from app.models import IncidentType
from app.models.session import transaction_context
from app.services.base_service import CrudService


class IncidentTypeService(CrudService):
    model = IncidentType
    primary_key = 'id_incident_type'
    entity_name = 'incident_type'

    @classmethod
    def options(cls) -> list[dict]:
        """Solo id+descripcion, para el selector de tipo en un vale de almacen.
        A proposito no exige el permiso de lectura de `incident_type` (modulo
        `operaciones`): un Almacenista levanta vales sin tener ese modulo.
        """
        with transaction_context() as session:
            filas = (
                session.query(IncidentType.id_incident_type, IncidentType.incident_type_description)
                .filter(IncidentType.deletion_date.is_(None))
                .order_by(IncidentType.incident_type_description)
                .all()
            )
            return [
                {'id_incident_type': fila[0], 'incident_type_description': fila[1]}
                for fila in filas
            ]
