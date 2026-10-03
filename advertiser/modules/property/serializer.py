from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.classes.serializer_fields import image_url
from core.models import Feature, Property, PropertyPhoto
from core.modules.property.serializer import (
    PropertyFeeSerializer,
    cover_photo_url,
    photo_display_url,
)

PRICE_FIELDS = ("sale_price", "rent_price", "seasonal_rent_price")


class AdvertiserPhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    is_hosted = serializers.BooleanField(read_only=True)

    class Meta:
        model = PropertyPhoto
        fields = ("id", "url", "thumbnail_url", "sort_order", "is_cover", "is_hosted")

    def get_url(self, obj):
        return photo_display_url(obj, self.context.get("request"))

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        return image_url(obj.thumbnail, request) if obj.thumbnail else photo_display_url(obj, request)


class AdvertiserPropertySerializer(serializers.ModelSerializer):
    custom_neighborhood_name = serializers.CharField(
        source="neighborhood_name", max_length=120, required=False, allow_blank=True
    )
    features = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Feature.objects.filter(is_active=True), required=False
    )
    fees = PropertyFeeSerializer(many=True, required=False)

    class Meta:
        model = Property
        fields = (
            "id",
            "reference_code",
            "is_active",
            "is_featured",
            "property_type",
            "city",
            "neighborhood",
            "custom_neighborhood_name",
            "is_in_condominium",
            "bedrooms",
            "suites",
            "bathrooms",
            "parking_spaces",
            "built_area",
            "total_area",
            "sale_price",
            "rent_price",
            "seasonal_rent_price",
            "fees",
            "description",
            "features",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        """Exige ao menos um preço (venda, locação ou temporada) no resultado final."""
        if self.partial and not any(field in attrs for field in PRICE_FIELDS):
            return attrs
        merged = (attrs.get(field, getattr(self.instance, field, None)) for field in PRICE_FIELDS)
        if not any(merged):
            raise serializers.ValidationError(
                {"sale_price": [_("Informe ao menos um preço: venda, locação ou temporada.")]}
            )
        return attrs


class AdvertiserPropertyDetailSerializer(serializers.ModelSerializer):
    property_type = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    neighborhood = serializers.SerializerMethodField()
    custom_neighborhood_name = serializers.CharField(source="neighborhood_name", read_only=True)
    features = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    feature_names = serializers.SerializerMethodField()
    condominium_feature_names = serializers.SerializerMethodField()
    fees = PropertyFeeSerializer(many=True, read_only=True)
    photos = AdvertiserPhotoSerializer(many=True, read_only=True)
    cover_photo_url = serializers.SerializerMethodField()
    views_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Property
        fields = (
            "id",
            "reference_code",
            "slug",
            "title",
            "status",
            "is_active",
            "is_featured",
            "property_type",
            "city",
            "neighborhood",
            "custom_neighborhood_name",
            "is_in_condominium",
            "bedrooms",
            "suites",
            "bathrooms",
            "parking_spaces",
            "built_area",
            "total_area",
            "description",
            "features",
            "feature_names",
            "condominium_feature_names",
            "fees",
            "sale_price",
            "rent_price",
            "seasonal_rent_price",
            "photos",
            "cover_photo_url",
            "views_count",
            "created_at",
            "updated_at",
        )

    def get_property_type(self, obj):
        return {
            "id": obj.property_type_id,
            "name": obj.property_type.name,
            "slug": obj.property_type.slug,
        }

    def get_city(self, obj):
        return {
            "id": obj.city_id,
            "name": obj.city.name,
            "slug": obj.city.slug,
            "state_code": obj.city.state.code,
        }

    def get_neighborhood(self, obj):
        if not obj.neighborhood_id:
            return None
        return {
            "id": obj.neighborhood_id,
            "name": obj.neighborhood.name,
            "slug": obj.neighborhood.slug,
        }

    def get_feature_names(self, obj):
        return [f.name for f in obj.features.all() if f.scope == Feature.Scope.PROPERTY]

    def get_condominium_feature_names(self, obj):
        return [f.name for f in obj.features.all() if f.scope == Feature.Scope.CONDOMINIUM]

    def get_cover_photo_url(self, obj):
        return cover_photo_url(obj, self.context.get("request"))
