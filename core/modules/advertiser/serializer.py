from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField
from core.models import Advertiser, AdvertiserIntegration, City

ADVERTISER_WRITE_FIELDS = (
    "user",
    "portal",
    "plan",
    "type",
    "name",
    "slug",
    "document",
    "email",
    "phone",
    "phone_secondary",
    "whatsapp",
    "website",
    "address",
    "creci",
    "contact_name",
    "responsible_broker",
    "notes",
    "coupon",
    "is_published",
    "accepted_terms_at",
    "notify_by_email",
    "has_hotsite",
    "has_realtor_page",
    "receives_property_requests",
    "property_limit",
    "photo_limit",
    "featured_limit",
    "super_featured_limit",
)


class AdvertiserCityField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return getattr(value, "city_id", None) or value.pk


class AdvertiserIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvertiserIntegration
        fields = (
            "integrator",
            "xml_url",
            "xml_default_url",
            "api_token",
            "vista_portal_key",
            "vista_customer_code",
            "vista_customer_key",
            "vista_api_url",
            "save_all_images",
            "skip_thumbnails",
            "is_active",
            "last_imported_at",
        )
        read_only_fields = ("last_imported_at",)
        extra_kwargs = {
            "api_token": {"write_only": True},
            "vista_portal_key": {"write_only": True},
            "vista_customer_code": {"write_only": True},
            "vista_customer_key": {"write_only": True},
            "vista_api_url": {"write_only": True},
        }


class AdvertiserIntegrationDetailSerializer(serializers.ModelSerializer):
    integrator_name = serializers.CharField(
        source="integrator.name", read_only=True, allow_null=True
    )
    has_api_token = serializers.SerializerMethodField()
    has_vista_credentials = serializers.SerializerMethodField()

    class Meta:
        model = AdvertiserIntegration
        fields = (
            "id",
            "integrator",
            "integrator_name",
            "xml_url",
            "xml_default_url",
            "save_all_images",
            "skip_thumbnails",
            "is_active",
            "last_imported_at",
            "has_api_token",
            "has_vista_credentials",
        )

    def get_has_api_token(self, obj):
        return bool(obj.api_token)

    def get_has_vista_credentials(self, obj):
        return bool(obj.vista_customer_code and obj.vista_customer_key)


class AdvertiserSerializer(serializers.ModelSerializer):
    integration = AdvertiserIntegrationSerializer(required=False, allow_null=True)
    cities = AdvertiserCityField(
        many=True, queryset=City.objects.all(), required=False, source="advertiser_cities"
    )
    logo_url = ImageUrlField(source="logo")

    class Meta:
        model = Advertiser
        fields = (
            "id",
            *ADVERTISER_WRITE_FIELDS,
            "logo",
            "logo_url",
            "integration",
            "cities",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "logo": {"write_only": True, "required": False, "allow_null": True},
        }


class AdvertiserListSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    properties_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Advertiser
        fields = (
            "id",
            "name",
            "slug",
            "type",
            "email",
            "phone",
            "plan",
            "plan_name",
            "portal",
            "portal_name",
            "is_published",
            "properties_count",
            "created_at",
        )


class AdvertiserDetailSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True, allow_null=True)
    logo_url = ImageUrlField(source="logo")
    integration = AdvertiserIntegrationDetailSerializer(read_only=True, allow_null=True)
    cities = AdvertiserCityField(many=True, read_only=True, source="advertiser_cities")
    properties_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Advertiser
        fields = (
            "id",
            *ADVERTISER_WRITE_FIELDS,
            "user_email",
            "portal_name",
            "plan_name",
            "logo_url",
            "integration",
            "cities",
            "properties_count",
            "legacy_id",
            "created_at",
            "updated_at",
        )
