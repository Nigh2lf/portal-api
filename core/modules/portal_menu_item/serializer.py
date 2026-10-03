from rest_framework import serializers

from core.models import PortalMenuItem


class PortalMenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalMenuItem
        fields = (
            "id",
            "portal",
            "label",
            "path",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_path(self, value):
        value = value.strip()
        if not (value.startswith("/") or value.startswith("http://") or value.startswith("https://")):
            raise serializers.ValidationError("Informe um caminho iniciado por / ou uma URL completa.")
        return value


class PortalMenuItemListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    portal_slug = serializers.CharField(source="portal.slug", read_only=True)

    class Meta:
        model = PortalMenuItem
        fields = (
            "id",
            "portal",
            "portal_name",
            "portal_slug",
            "label",
            "path",
            "sort_order",
            "is_active",
            "updated_at",
        )


class PortalMenuItemDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = PortalMenuItem
        fields = (
            "id",
            "portal",
            "portal_name",
            "label",
            "path",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
