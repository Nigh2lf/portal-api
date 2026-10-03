from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import BlogPost, Tip


class PublicPostListSerializer(serializers.ModelSerializer):
    cover_image_url = ImageUrlField(source="cover_image")

    class Meta:
        model = BlogPost
        fields = ("id", "slug", "title", "excerpt", "author_name", "cover_image_url", "published_at")


class PublicPostDetailSerializer(PublicPostListSerializer):
    portal = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(PublicPostListSerializer.Meta):
        fields = (*PublicPostListSerializer.Meta.fields, "body", "portal")


class PublicTipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tip
        fields = ("id", "title", "body", "sort_order")
