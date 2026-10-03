from core.models import PropertyType
from core.services import SluggedCrudService


class PropertyTypeService(SluggedCrudService):
    model = PropertyType
