from rest_framework import serializers

from core.models import PropertyType


class PropertyTypeSerializer(serializers.ModelSerializer):
    import_aliases = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False
    )

    class Meta:
        model = PropertyType
        fields = (
            "id",
            "name",
            "slug",
            "import_aliases",
            "mercadolivre_category",
            "is_residential",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class PropertyTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = (
            "id",
            "name",
            "slug",
            "is_residential",
            "is_active",
            "sort_order",
            "created_at",
        )


class PropertyTypeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = (
            "id",
            "name",
            "slug",
            "import_aliases",
            "mercadolivre_category",
            "is_residential",
            "is_active",
            "sort_order",
            "legacy_id",
            "created_at",
            "updated_at",
        )
