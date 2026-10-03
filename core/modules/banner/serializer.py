from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import Banner


class BannerSerializer(serializers.ModelSerializer):
    home_image_url = ImageUrlField(source="home_image")
    inner_image_url = ImageUrlField(source="inner_image")

    class Meta:
        model = Banner
        fields = (
            "id",
            "portal",
            "home_image",
            "home_image_url",
            "inner_image",
            "inner_image_url",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "home_image": {"write_only": True},
            "inner_image": {"write_only": True, "required": False, "allow_null": True},
        }


class BannerListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)
    home_image_url = ImageUrlField(source="home_image")
    inner_image_url = ImageUrlField(source="inner_image")

    class Meta:
        model = Banner
        fields = (
            "id",
            "portal",
            "portal_name",
            "home_image_url",
            "inner_image_url",
            "is_active",
            "created_at",
        )


class BannerDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)
    home_image_url = ImageUrlField(source="home_image")
    inner_image_url = ImageUrlField(source="inner_image")

    class Meta:
        model = Banner
        fields = (
            "id",
            "portal",
            "portal_name",
            "home_image_url",
            "inner_image_url",
            "is_active",
            "created_at",
            "updated_at",
        )
