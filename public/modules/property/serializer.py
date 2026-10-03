from rest_framework import serializers

from core.classes.serializer_fields import image_url
from core.models import Advertiser, Property, PropertyFee, PropertyPhoto
from core.modules.property.serializer import photo_display_url
from public.modules.portal.serializer import PublicPropertyCardSerializer


class PublicPhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = ("id", "url", "thumbnail_url", "sort_order", "is_cover")

    def get_url(self, obj):
        return photo_display_url(obj, self.context.get("request"))

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        return image_url(obj.thumbnail, request) if obj.thumbnail else photo_display_url(obj, request)


class PublicFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFee
        fields = ("description", "amount", "period", "notes")


class PublicAdvertiserSerializer(serializers.ModelSerializer):
    """Bloco público do anunciante: contatos são públicos no site (como no legado)."""

    logo_url = serializers.SerializerMethodField()
    hotsite_slug = serializers.SerializerMethodField()
    total_properties = serializers.IntegerField(read_only=True, default=0)
    total_sale = serializers.IntegerField(read_only=True, default=0)
    total_rent = serializers.IntegerField(read_only=True, default=0)
    total_seasonal = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Advertiser
        fields = (
            "id",
            "slug",
            "type",
            "name",
            "creci",
            "logo_url",
            "phone",
            "phone_secondary",
            "whatsapp",
            "email",
            "website",
            "address",
            "has_hotsite",
            "hotsite_slug",
            "total_properties",
            "total_sale",
            "total_rent",
            "total_seasonal",
        )

    def get_logo_url(self, obj):
        return image_url(obj.logo, self.context.get("request"))

    def get_hotsite_slug(self, obj):
        return obj.slug if obj.has_hotsite else None


class PublicPropertyDetailSerializer(serializers.ModelSerializer):
    property_type = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    neighborhood = serializers.SerializerMethodField()
    neighborhood_name = serializers.SerializerMethodField()
    state_code = serializers.CharField(source="city.state.code", read_only=True)
    features = serializers.SerializerMethodField()
    condominium_features = serializers.SerializerMethodField()
    fees = PublicFeeSerializer(many=True, read_only=True)
    photos = PublicPhotoSerializer(many=True, read_only=True)
    advertiser = PublicAdvertiserSerializer(read_only=True)

    class Meta:
        model = Property
        fields = (
            "id",
            "reference_code",
            "slug",
            "title",
            "is_featured",
            "property_type",
            "city",
            "neighborhood",
            "neighborhood_name",
            "state_code",
            "is_in_condominium",
            "bedrooms",
            "suites",
            "bathrooms",
            "parking_spaces",
            "built_area",
            "total_area",
            "description",
            "features",
            "condominium_features",
            "fees",
            "sale_price",
            "rent_price",
            "seasonal_rent_price",
            "photos",
            "advertiser",
            "published_at",
            "created_at",
            "updated_at",
        )

    def get_property_type(self, obj):
        return {"id": obj.property_type_id, "name": obj.property_type.name, "slug": obj.property_type.slug}

    def get_city(self, obj):
        return {"id": obj.city_id, "name": obj.city.name, "slug": obj.city.slug, "state_code": obj.city.state.code}

    def get_neighborhood(self, obj):
        if not obj.neighborhood:
            return None
        return {"id": obj.neighborhood_id, "name": obj.neighborhood.name, "slug": obj.neighborhood.slug}

    def get_neighborhood_name(self, obj):
        return obj.neighborhood.name if obj.neighborhood else (obj.neighborhood_name or None)

    def get_features(self, obj):
        return [f.name for f in obj.features.all() if f.scope == "PROPERTY"]

    def get_condominium_features(self, obj):
        return [f.name for f in obj.features.all() if f.scope == "CONDOMINIUM"]


class PublicSearchResultSerializer(serializers.Serializer):
    results = PublicPropertyCardSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    counters = serializers.DictField()
    max_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    applied = serializers.SerializerMethodField()

    def get_applied(self, obj):
        r = obj["applied"]
        return {
            "property_type": {"name": r["property_type"].name, "slug": r["property_type"].slug} if r["property_type"] else None,
            "city": {"name": r["city"].name, "slug": r["city"].slug, "state_code": r["city"].state.code} if r["city"] else None,
            "neighborhood": {"name": r["neighborhood"].name, "slug": r["neighborhood"].slug} if r["neighborhood"] else None,
        }


class PublicInquirySerializer(serializers.Serializer):
    property = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=120)
    phone = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")
    message = serializers.CharField(max_length=4000)
    contact_preferences = serializers.ListField(
        child=serializers.ChoiceField(choices=["WHATSAPP", "PHONE", "EMAIL"]), required=False, default=list
    )
    recaptcha_token = serializers.CharField(required=False, allow_blank=True)


class PublicContactClickSerializer(serializers.Serializer):
    property = serializers.UUIDField(required=False, allow_null=True)
    advertiser = serializers.UUIDField(required=False, allow_null=True)
    channel = serializers.ChoiceField(choices=["PHONE", "WHATSAPP"])

    def validate(self, attrs):
        if not attrs.get("property") and not attrs.get("advertiser"):
            raise serializers.ValidationError({"advertiser": ["Informe o imóvel ou o anunciante."]})
        return attrs
