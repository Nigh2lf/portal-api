from rest_framework import serializers

from core.models import AdPlacement, Plan


class PublicPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "slug",
            "name",
            "monthly_price",
            "property_limit",
            "photo_limit",
            "featured_limit",
            "has_realtor_page",
            "receives_property_requests",
            "has_hotsite",
            "is_recommended",
            "is_owner_only",
            "sort_order",
        )


class PublicAdPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlacement
        fields = ("code", "name", "page", "kind", "width", "height", "monthly_price", "notes")
