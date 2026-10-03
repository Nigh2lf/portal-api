from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import City, Portal, PortalMenuItem


class PortalMenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalMenuItem
        fields = ("id", "label", "path", "sort_order", "is_active")
        read_only_fields = ("id",)


class PortalSerializer(serializers.ModelSerializer):
    extra_domains = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False
    )
    cities = serializers.PrimaryKeyRelatedField(
        many=True, queryset=City.objects.all(), required=False
    )
    combined_portals = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Portal.objects.all(), required=False
    )
    menu_items = PortalMenuItemSerializer(many=True, required=False)
    logo_url = ImageUrlField(source="logo")
    logo_mobile_url = ImageUrlField(source="logo_mobile")
    og_image_url = ImageUrlField(source="og_image")
    watermark_url = ImageUrlField(source="watermark")

    class Meta:
        model = Portal
        fields = (
            "id",
            "slug",
            "name",
            "domain",
            "extra_domains",
            "is_active",
            "main_city",
            "cities",
            "combined_portals",
            "show_city_filter",
            "email",
            "phone",
            "whatsapp",
            "address",
            "seo_title",
            "seo_description",
            "seo_keywords",
            "about_text",
            "facebook_url",
            "instagram_url",
            "ga4_measurement_id",
            "recaptcha_site_key",
            "logo",
            "logo_url",
            "logo_mobile",
            "logo_mobile_url",
            "og_image",
            "og_image_url",
            "watermark",
            "watermark_url",
            "primary_color",
            "secondary_color",
            "realtors_page_slug",
            "results_per_page",
            "thumbnail_max_width",
            "thumbnail_max_height",
            "watermark_position",
            "menu_items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "logo": {"write_only": True, "required": False, "allow_null": True},
            "logo_mobile": {"write_only": True, "required": False, "allow_null": True},
            "og_image": {"write_only": True, "required": False, "allow_null": True},
            "watermark": {"write_only": True, "required": False, "allow_null": True},
        }


class PortalListSerializer(serializers.ModelSerializer):
    main_city_name = serializers.CharField(source="main_city.name", read_only=True)
    logo_url = ImageUrlField(source="logo")

    class Meta:
        model = Portal
        fields = (
            "id",
            "name",
            "slug",
            "domain",
            "is_active",
            "main_city",
            "main_city_name",
            "email",
            "logo_url",
            "created_at",
        )


class PortalDetailSerializer(serializers.ModelSerializer):
    main_city_name = serializers.CharField(source="main_city.name", read_only=True)
    cities = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    combined_portals = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    menu_items = PortalMenuItemSerializer(many=True, read_only=True)
    logo_url = ImageUrlField(source="logo")
    logo_mobile_url = ImageUrlField(source="logo_mobile")
    og_image_url = ImageUrlField(source="og_image")
    watermark_url = ImageUrlField(source="watermark")

    class Meta:
        model = Portal
        fields = (
            "id",
            "slug",
            "name",
            "domain",
            "extra_domains",
            "is_active",
            "main_city",
            "main_city_name",
            "cities",
            "combined_portals",
            "show_city_filter",
            "email",
            "phone",
            "whatsapp",
            "address",
            "seo_title",
            "seo_description",
            "seo_keywords",
            "about_text",
            "facebook_url",
            "instagram_url",
            "ga4_measurement_id",
            "recaptcha_site_key",
            "logo_url",
            "logo_mobile_url",
            "og_image_url",
            "watermark_url",
            "primary_color",
            "secondary_color",
            "realtors_page_slug",
            "results_per_page",
            "thumbnail_max_width",
            "thumbnail_max_height",
            "watermark_position",
            "menu_items",
            "legacy_id",
            "created_at",
            "updated_at",
        )
