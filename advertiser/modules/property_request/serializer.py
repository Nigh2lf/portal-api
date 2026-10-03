from rest_framework import serializers

from core.models import PropertyRequest


class AdvertiserPropertyRequestSerializer(serializers.ModelSerializer):
    property_type_name = serializers.CharField(
        source="property_type.name", read_only=True, allow_null=True
    )
    city_name = serializers.CharField(source="city.name", read_only=True, allow_null=True)
    neighborhood_name = serializers.CharField(
        source="neighborhood.name", read_only=True, allow_null=True
    )
    funding = serializers.SerializerMethodField()

    class Meta:
        model = PropertyRequest
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "purpose",
            "property_type_name",
            "city_name",
            "neighborhood_name",
            "min_price",
            "max_price",
            "is_in_condominium",
            "funding",
            "message",
            "created_at",
        )

    def get_funding(self, obj):
        return obj.funding or None
