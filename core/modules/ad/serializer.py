from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import Ad


class AdSerializer(serializers.ModelSerializer):
    image_url = ImageUrlField(source="image")

    class Meta:
        model = Ad
        fields = (
            "id",
            "portal",
            "placement",
            "name",
            "image",
            "image_url",
            "link_url",
            "open_in_new_tab",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {"image": {"write_only": True}}

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at < starts_at:
            raise serializers.ValidationError(
                {"ends_at": [_("A data final deve ser posterior à inicial.")]}
            )
        return attrs


class AdListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    placement_code = serializers.CharField(source="placement.code", read_only=True)
    placement_name = serializers.CharField(source="placement.name", read_only=True)
    image_url = ImageUrlField(source="image")

    class Meta:
        model = Ad
        fields = (
            "id",
            "name",
            "portal",
            "portal_name",
            "placement",
            "placement_code",
            "placement_name",
            "image_url",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
        )


class AdDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    placement_code = serializers.CharField(source="placement.code", read_only=True)
    placement_name = serializers.CharField(source="placement.name", read_only=True)
    image_url = ImageUrlField(source="image")

    class Meta:
        model = Ad
        fields = (
            "id",
            "name",
            "portal",
            "portal_name",
            "placement",
            "placement_code",
            "placement_name",
            "image_url",
            "link_url",
            "open_in_new_tab",
            "starts_at",
            "ends_at",
            "is_active",
            "legacy_id",
            "created_at",
            "updated_at",
        )
