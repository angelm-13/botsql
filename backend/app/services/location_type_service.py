from app.models import LocationType
from app.services.base_service import CrudService


class LocationTypeService(CrudService):
    model = LocationType
    primary_key = 'id_location_type'
    entity_name = 'location_type'
