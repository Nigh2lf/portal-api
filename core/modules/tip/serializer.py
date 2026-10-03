from rest_framework import serializers

from core.models import Tip


class TipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tip
        fields = (
            "id",
            "portal",
            "title",
            "body",
            "is_active",
            "published_at",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TipListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)

    class Meta:
        model = Tip
        fields = (
            "id",
            "title",
            "portal",
            "portal_name",
            "is_active",
            "published_at",
            "sort_order",
            "created_at",
        )


class TipDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)

    class Meta:
        model = Tip
        fields = (
            "id",
            "title",
            "body",
            "portal",
            "portal_name",
            "is_active",
            "published_at",
            "sort_order",
            "legacy_id",
            "created_at",
            "updated_at",
        )
