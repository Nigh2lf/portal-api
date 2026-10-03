"""Serializer do model `PublicAsset` (imagens públicas para landing/marketing)."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.models import PublicAsset


class PublicAssetSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PublicAsset
        fields = (
            "id",
            "name",
            "description",
            "image",
            "image_url",
            "is_active",
            "uploaded_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "uploaded_by", "image_url", "created_at", "updated_at")
        extra_kwargs = {"image": {"write_only": True, "required": True}}

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image_url(self, obj):
        try:
            return obj.image.url if obj.image else None
        except Exception:  # noqa: BLE001 - storage pode falhar; nunca quebrar serializer
            return None
