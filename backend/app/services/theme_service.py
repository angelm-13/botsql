from app.models import Theme
from app.services.base_service import CrudService


class ThemeService(CrudService):
    model = Theme
    primary_key = 'id_theme'
    entity_name = 'theme'
