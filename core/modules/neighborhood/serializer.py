from rest_framework import serializers

from core.models import Neighborhood


class NeighborhoodSerializer(serializers.ModelSerializer):
    import_aliases = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False
    )

    class Meta:
        model = Neighborhood
        fields = (
            "id",
            "city",
            "name",
            "slug",
            "import_aliases",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}
        validators = []


class NeighborhoodListSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    state_code = serializers.CharField(source="city.state.code", read_only=True)

    class Meta:
        model = Neighborhood
        fields = (
            "id",
            "name",
            "slug",
            "city",
            "city_name",
            "state_code",
            "is_active",
            "created_at",
        )


class NeighborhoodDetailSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    state_code = serializers.CharField(source="city.state.code", read_only=True)

    class Meta:
        model = Neighborhood
        fields = (
            "id",
            "name",
            "slug",
            "city",
            "city_name",
            "state_code",
            "import_aliases",
            "is_active",
            "legacy_id",
            "created_at",
            "updated_at",
        )
