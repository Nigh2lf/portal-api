import re

from rest_framework import serializers

from core.classes.serializer_fields import ImageUrlField, image_url
from core.models import Ad, Banner, City, Feature, Neighborhood, Portal, PortalMenuItem, Property, PropertyType
from core.modules.property.serializer import cover_photo_url

EXCERPT_LENGTH = 220


class PublicCitySerializer(serializers.ModelSerializer):
    state_code = serializers.CharField(source="state.code", read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "slug", "state_code")


class PublicNeighborhoodSerializer(serializers.ModelSerializer):
    city_slug = serializers.CharField(source="city.slug", read_only=True)

    class Meta:
        model = Neighborhood
        fields = ("id", "name", "slug", "city", "city_slug")


class PublicPropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = ("id", "name", "slug", "is_residential")


class PublicFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ("id", "name", "slug", "scope")


class PublicMenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalMenuItem
        fields = ("label", "path", "sort_order")


class PublicPortalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ("id", "slug", "name", "domain")


class PublicPortalSerializer(serializers.ModelSerializer):
    main_city = PublicCitySerializer(read_only=True)
    cities = serializers.SerializerMethodField()
    combined_portals = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    menu_items = serializers.SerializerMethodField()
    logo_url = ImageUrlField(source="logo")
    logo_mobile_url = ImageUrlField(source="logo_mobile")
    og_image_url = ImageUrlField(source="og_image")
    total_properties = serializers.IntegerField(read_only=True)
    show_city_filter = serializers.SerializerMethodField()

    class Meta:
        model = Portal
        fields = (
            "id",
            "slug",
            "name",
            "domain",
            "extra_domains",
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
            "logo_url",
            "logo_mobile_url",
            "og_image_url",
            "primary_color",
            "secondary_color",
            "realtors_page_slug",
            "results_per_page",
            "menu_items",
            "total_properties",
        )

    def get_cities(self, obj):
        return PublicCitySerializer([pc.city for pc in obj.portal_cities.all()], many=True).data

    def get_show_city_filter(self, obj):
        # Portal com mais de uma cidade sempre deixa o visitante escolher a cidade na busca.
        return obj.show_city_filter or len(obj.portal_cities.all()) > 1

    def get_menu_items(self, obj):
        itens = [m for m in obj.menu_items.all() if m.is_active]
        return PublicMenuItemSerializer(sorted(itens, key=lambda m: m.sort_order), many=True).data


class PublicPropertyCardSerializer(serializers.ModelSerializer):
    property_type_name = serializers.CharField(source="property_type.name", read_only=True)
    property_type_slug = serializers.CharField(source="property_type.slug", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    city_slug = serializers.CharField(source="city.slug", read_only=True)
    state_code = serializers.CharField(source="city.state.code", read_only=True)
    neighborhood_name = serializers.SerializerMethodField()
    neighborhood_slug = serializers.CharField(source="neighborhood.slug", read_only=True, default=None)
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    advertiser_slug = serializers.SerializerMethodField()
    advertiser_logo_url = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()
    photos_count = serializers.IntegerField(read_only=True)
    features = serializers.SerializerMethodField()
    description_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "reference_code",
            "slug",
            "title",
            "ad_type",
            "property_type_name",
            "property_type_slug",
            "city_name",
            "city_slug",
            "state_code",
            "neighborhood_name",
            "neighborhood_slug",
            "bedrooms",
            "suites",
            "bathrooms",
            "parking_spaces",
            "built_area",
            "total_area",
            "sale_price",
            "rent_price",
            "seasonal_rent_price",
            "cover_photo_url",
            "photos_count",
            "features",
            "description_excerpt",
            "advertiser_name",
            "advertiser_slug",
            "advertiser_logo_url",
            "updated_at",
        )

    def get_neighborhood_name(self, obj):
        return obj.neighborhood.name if obj.neighborhood else (obj.neighborhood_name or None)

    def get_advertiser_slug(self, obj):
        return obj.advertiser.slug if obj.advertiser.has_hotsite else None

    def get_advertiser_logo_url(self, obj):
        return image_url(obj.advertiser.logo, self.context.get("request"))

    def get_cover_photo_url(self, obj):
        return cover_photo_url(obj, self.context.get("request"))

    def get_features(self, obj):
        return [f.name for f in obj.features.all()]

    def get_description_excerpt(self, obj):
        texto = re.sub(r"<[^>]+>", " ", obj.description or "")
        texto = re.sub(r"\s+", " ", texto).strip()
        if len(texto) <= EXCERPT_LENGTH:
            return texto
        return texto[:EXCERPT_LENGTH].rsplit(" ", 1)[0] + "…"


class PublicBannerSerializer(serializers.ModelSerializer):
    home_image_url = ImageUrlField(source="home_image")
    inner_image_url = ImageUrlField(source="inner_image")

    class Meta:
        model = Banner
        fields = ("id", "home_image_url", "inner_image_url")


class PublicAdSerializer(serializers.ModelSerializer):
    image_url = ImageUrlField(source="image")
    placement_code = serializers.CharField(source="placement.code", read_only=True)
    placement_page = serializers.CharField(source="placement.page", read_only=True)
    placement_kind = serializers.CharField(source="placement.kind", read_only=True)

    class Meta:
        model = Ad
        fields = ("id", "name", "image_url", "link_url", "open_in_new_tab", "placement_code", "placement_page", "placement_kind", "starts_at", "ends_at")
