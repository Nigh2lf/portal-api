from rest_framework import serializers

from core.models import Portal, Property
from core.services.public_cache import SCOPES


class PublicCacheInvalidateSerializer(serializers.Serializer):
    portal = serializers.SlugField(required=False, allow_blank=True, default="")
    scopes = serializers.ListField(child=serializers.ChoiceField(choices=list(SCOPES)), required=False, default=list)
    property_code = serializers.CharField(required=False, allow_blank=True, default="", max_length=45)

    def validate_portal(self, value):
        if value and not Portal.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Portal não encontrado.")
        return value

    def validate(self, attrs):
        codigo = attrs["property_code"].strip()
        if not codigo:
            attrs["items"] = []
            return attrs
        imoveis = Property.objects.filter(reference_code__iexact=codigo, deleted_at__isnull=True)
        if attrs["portal"]:
            imoveis = imoveis.filter(advertiser__portal__slug=attrs["portal"])
        itens = {v.lower() for slug, code in imoveis.values_list("slug", "reference_code") for v in (slug, code) if v}
        if not itens:
            raise serializers.ValidationError({"property_code": ["Nenhum imóvel com este código."]})
        attrs["items"] = sorted(itens)
        return attrs
