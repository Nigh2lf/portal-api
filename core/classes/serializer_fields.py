from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


def image_url(file, request=None):
    """Retorna a URL pública (absoluta quando há request) do arquivo ou `None` se vazio."""
    try:
        if not file:
            return None
        url = file.url
    except Exception:  # noqa: BLE001 - storage pode falhar; nunca quebrar serializer
        return None
    if request is not None and url.startswith("/"):
        return request.build_absolute_uri(url)
    return url


@extend_schema_field(serializers.URLField(allow_null=True))
class ImageUrlField(serializers.ReadOnlyField):
    def to_representation(self, value):
        request = self.context.get("request") if self.context else None
        return image_url(value, request)
