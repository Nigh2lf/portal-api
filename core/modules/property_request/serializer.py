from rest_framework import serializers

from core.models import PropertyRequest


class PropertyRequestListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    advertiser_name = serializers.CharField(
        source="advertiser.name", read_only=True, allow_null=True
    )
    property_type_name = serializers.CharField(
        source="property_type.name", read_only=True, allow_null=True
    )
    city_name = serializers.CharField(source="city.name", read_only=True, allow_null=True)
    neighborhood_name = serializers.CharField(
        source="neighborhood.name", read_only=True, allow_null=True
    )

    class Meta:
        model = PropertyRequest
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "purpose",
            "portal",
            "portal_name",
            "advertiser",
            "advertiser_name",
            "property_type",
            "property_type_name",
            "city",
            "city_name",
            "neighborhood",
            "neighborhood_name",
            "min_price",
            "max_price",
            "is_partner_broadcast",
            "created_at",
        )


class PropertyRequestDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    advertiser_name = serializers.CharField(
        source="advertiser.name", read_only=True, allow_null=True
    )
    property_type_name = serializers.CharField(
        source="property_type.name", read_only=True, allow_null=True
    )
    city_name = serializers.CharField(source="city.name", read_only=True, allow_null=True)
    neighborhood_name = serializers.CharField(
        source="neighborhood.name", read_only=True, allow_null=True
    )

    class Meta:
        model = PropertyRequest
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "purpose",
            "funding",
            "message",
            "portal",
            "portal_name",
            "advertiser",
            "advertiser_name",
            "property_type",
            "property_type_name",
            "city",
            "city_name",
            "neighborhood",
            "neighborhood_name",
            "min_price",
            "max_price",
            "is_in_condominium",
            "is_partner_broadcast",
            "ip_address",
            "legacy_id",
            "created_at",
            "updated_at",
        )
