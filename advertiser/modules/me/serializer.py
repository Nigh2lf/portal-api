from rest_framework import serializers

from core.models import Advertiser, AdvertiserIntegration, Plan


class AdvertiserPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "slug",
            "name",
            "property_limit",
            "photo_limit",
            "featured_limit",
            "has_hotsite",
            "has_realtor_page",
            "receives_property_requests",
            "monthly_price",
        )


class AdvertiserMeSerializer(serializers.ModelSerializer):
    advertiser_id = serializers.UUIDField(source="id", read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    portal_slug = serializers.CharField(source="portal.slug", read_only=True)
    plan = AdvertiserPlanSerializer(read_only=True)
    has_automatic_import = serializers.SerializerMethodField()

    class Meta:
        model = Advertiser
        fields = (
            "advertiser_id",
            "user_id",
            "name",
            "email",
            "type",
            "portal_slug",
            "plan",
            "has_automatic_import",
            "has_hotsite",
            "is_published",
            "document",
            "phone",
            "phone_secondary",
            "whatsapp",
            "contact_name",
            "website",
            "address",
            "creci",
            "created_at",
        )

    def get_has_automatic_import(self, obj):
        return AdvertiserIntegration.objects.filter(advertiser=obj).exclude(xml_url="").exists()


class AdvertiserMeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertiser
        fields = (
            "name",
            "email",
            "phone",
            "phone_secondary",
            "whatsapp",
            "contact_name",
            "website",
            "address",
            "creci",
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128)
