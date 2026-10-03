from rest_framework import serializers

from core.models import PropertyInquiry


class AdvertiserInquirySerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True, allow_null=True)
    property_slug = serializers.CharField(source="property.slug", read_only=True, allow_null=True)
    portal_slug = serializers.CharField(source="portal.slug", read_only=True)

    class Meta:
        model = PropertyInquiry
        fields = (
            "id",
            "property",
            "property_reference_code",
            "property_title",
            "property_slug",
            "portal_slug",
            "name",
            "email",
            "phone",
            "message",
            "contact_preferences",
            "is_mobile",
            "created_at",
        )
