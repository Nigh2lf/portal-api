from rest_framework import serializers

from core.models import City


class CitySerializer(serializers.ModelSerializer):
    import_aliases = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False
    )

    class Meta:
        model = City
        fields = (
            "id",
            "state",
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


class CityListSerializer(serializers.ModelSerializer):
    state_code = serializers.CharField(source="state.code", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "slug",
            "state",
            "state_code",
            "state_name",
            "is_active",
            "created_at",
        )


class CityDetailSerializer(serializers.ModelSerializer):
    state_code = serializers.CharField(source="state.code", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "slug",
            "state",
            "state_code",
            "state_name",
            "import_aliases",
            "is_active",
            "legacy_id",
            "created_at",
            "updated_at",
        )
