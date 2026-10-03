from rest_framework import serializers

from core.models import Plan

PLAN_FIELDS = (
    "id",
    "name",
    "slug",
    "monthly_price",
    "property_limit",
    "photo_limit",
    "featured_limit",
    "has_realtor_page",
    "receives_property_requests",
    "has_hotsite",
    "is_owner_only",
    "is_recommended",
    "is_active",
    "sort_order",
)


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (*PLAN_FIELDS, "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class PlanListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "name",
            "slug",
            "monthly_price",
            "property_limit",
            "photo_limit",
            "featured_limit",
            "is_recommended",
            "is_active",
            "sort_order",
            "created_at",
        )


class PlanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (*PLAN_FIELDS, "legacy_id", "created_at", "updated_at")
