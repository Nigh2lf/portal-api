from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


def image_url(file):
    """Retorna a URL pública do arquivo ou `None` se vazio/indisponível."""
    try:
        return file.url if file else None
    except Exception:  # noqa: BLE001 - storage pode falhar; nunca quebrar serializer
        return None


@extend_schema_field(serializers.URLField(allow_null=True))
class ImageUrlField(serializers.ReadOnlyField):
    def to_representation(self, value):
        return image_url(value)
