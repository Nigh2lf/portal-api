from rest_framework import serializers

from core.models import AdPlacement

AD_PLACEMENT_FIELDS = (
    "id",
    "code",
    "name",
    "page",
    "kind",
    "width",
    "height",
    "monthly_price",
    "notes",
    "is_active",
)


class AdPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlacement
        fields = (*AD_PLACEMENT_FIELDS, "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_code(self, value):
        return value.strip().upper()


class AdPlacementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlacement
        fields = (
            "id",
            "code",
            "name",
            "page",
            "kind",
            "width",
            "height",
            "monthly_price",
            "is_active",
            "created_at",
        )


class AdPlacementDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlacement
        fields = (*AD_PLACEMENT_FIELDS, "legacy_id", "created_at", "updated_at")
