from app.models import Location
from app.services.base_service import CrudService


class LocationService(CrudService):
    model = Location
    primary_key = 'id_location'
    entity_name = 'location'
