from core.models import Neighborhood
from core.services import SluggedCrudService


class NeighborhoodService(SluggedCrudService):
    model = Neighborhood
    slug_scope_fields = ("city",)
