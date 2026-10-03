from core.models import City
from core.services import SluggedCrudService


class CityService(SluggedCrudService):
    model = City
    slug_scope_fields = ("state",)
