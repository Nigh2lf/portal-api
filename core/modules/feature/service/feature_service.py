from core.models import Feature
from core.services import SluggedCrudService


class FeatureService(SluggedCrudService):
    model = Feature
    slug_scope_fields = ("scope",)
