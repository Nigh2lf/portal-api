from rest_framework import serializers

from core.models import PropertyInquiry


class PropertyInquiryListSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = PropertyInquiry
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "advertiser",
            "advertiser_name",
            "portal",
            "portal_name",
            "property",
            "property_reference_code",
            "forwarded_to_crm_at",
            "created_at",
        )


class PropertyInquiryDetailSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True, allow_null=True)

    class Meta:
        model = PropertyInquiry
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "message",
            "contact_preferences",
            "advertiser",
            "advertiser_name",
            "portal",
            "portal_name",
            "property",
            "property_title",
            "property_reference_code",
            "ip_address",
            "referer",
            "is_mobile",
            "forwarded_to_crm_at",
            "legacy_id",
            "created_at",
            "updated_at",
        )
