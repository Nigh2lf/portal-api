from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import BlogPost


class BlogPostSerializer(serializers.ModelSerializer):
    cover_image_url = ImageUrlField(source="cover_image")

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "portal",
            "title",
            "slug",
            "excerpt",
            "body",
            "author_name",
            "cover_image",
            "cover_image_url",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "cover_image": {"write_only": True, "required": False, "allow_null": True},
        }


class BlogPostListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)
    cover_image_url = ImageUrlField(source="cover_image")

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "title",
            "slug",
            "portal",
            "portal_name",
            "author_name",
            "cover_image_url",
            "is_published",
            "published_at",
            "created_at",
        )


class BlogPostDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True, allow_null=True)
    cover_image_url = ImageUrlField(source="cover_image")

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "title",
            "slug",
            "portal",
            "portal_name",
            "excerpt",
            "body",
            "author_name",
            "cover_image_url",
            "is_published",
            "published_at",
            "legacy_id",
            "created_at",
            "updated_at",
        )
