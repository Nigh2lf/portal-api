from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField, image_url
from core.models import Feature, Property, PropertyFee, PropertyPhoto

PROPERTY_WRITE_FIELDS = (
    "advertiser",
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
    "sale_price",
    "rent_price",
    "seasonal_rent_price",
    "published_at",
)


def neighborhood_display(obj):
    """Nome do bairro vinculado ou o texto livre de "outro bairro"."""
    if obj.neighborhood_id:
        return obj.neighborhood.name
    return obj.neighborhood_name or None


def photo_display_url(photo, request=None):
    """Foto em tamanho cheio: hospedada (URL absoluta) ou a externa do anunciante."""
    if photo.image:
        return image_url(photo.image, request)
    return photo.source_url or None


def cover_photo_url(obj, request=None):
    """Miniatura da capa (ou a própria foto, se não houver miniatura), das fotos já pré-carregadas."""
    photos = list(obj.photos.all())
    cover = next((photo for photo in photos if photo.is_cover), photos[0] if photos else None)
    if cover is None:
        return None
    return image_url(cover.thumbnail, request) if cover.thumbnail else photo_display_url(cover, request)


class PropertyPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    is_hosted = serializers.BooleanField(read_only=True)

    class Meta:
        model = PropertyPhoto
        fields = ("id", "image_url", "thumbnail_url", "is_hosted", "source_url", "sort_order", "is_cover")

    def get_image_url(self, obj):
        return photo_display_url(obj, self.context.get("request"))

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        return image_url(obj.thumbnail, request) if obj.thumbnail else photo_display_url(obj, request)


class PropertyFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFee
        fields = ("id", "description", "amount", "period", "notes")
        read_only_fields = ("id",)


class PropertyPhotoUploadSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField(), allow_empty=False)


class PropertyPhotoReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class PropertySerializer(serializers.ModelSerializer):
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
            *PROPERTY_WRITE_FIELDS,
            "features",
            "fees",
            "imported_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "imported_at", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "title": {"required": False, "allow_blank": True},
        }


class PropertyListSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    property_type_name = serializers.CharField(source="property_type.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    neighborhood_name = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "reference_code",
            "title",
            "slug",
            "status",
            "is_active",
            "is_featured",
            "advertiser",
            "advertiser_name",
            "property_type",
            "property_type_name",
            "city",
            "city_name",
            "neighborhood",
            "neighborhood_name",
            "sale_price",
            "rent_price",
            "seasonal_rent_price",
            "bedrooms",
            "parking_spaces",
            "cover_photo_url",
            "updated_at",
        )

    def get_neighborhood_name(self, obj):
        return neighborhood_display(obj)

    def get_cover_photo_url(self, obj):
        return cover_photo_url(obj, self.context.get("request"))


class PropertyDetailSerializer(serializers.ModelSerializer):
    custom_neighborhood_name = serializers.CharField(source="neighborhood_name", read_only=True)
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    advertiser_portal = serializers.UUIDField(source="advertiser.portal_id", read_only=True)
    property_type_name = serializers.CharField(source="property_type.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    state_code = serializers.CharField(source="city.state.code", read_only=True)
    neighborhood_name = serializers.SerializerMethodField()
    features = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    fees = PropertyFeeSerializer(many=True, read_only=True)
    cover_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            *PROPERTY_WRITE_FIELDS,
            "advertiser_name",
            "advertiser_portal",
            "property_type_name",
            "city_name",
            "state_code",
            "neighborhood_name",
            "features",
            "photos",
            "fees",
            "cover_photo_url",
            "imported_at",
            "legacy_id",
            "created_at",
            "updated_at",
        )

    def get_neighborhood_name(self, obj):
        return neighborhood_display(obj)

    def get_cover_photo_url(self, obj):
        return cover_photo_url(obj, self.context.get("request"))
