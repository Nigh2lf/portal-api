from rest_framework import serializers

from core.models import Feature


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = (
            "id",
            "scope",
            "name",
            "slug",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}
        validators = []


class FeatureListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ("id", "scope", "name", "slug", "is_active", "sort_order", "created_at")


class FeatureDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = (
            "id",
            "scope",
            "name",
            "slug",
            "is_active",
            "sort_order",
            "legacy_id",
            "created_at",
            "updated_at",
        )
