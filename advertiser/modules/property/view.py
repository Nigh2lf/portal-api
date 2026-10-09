from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from advertiser.modules.property.serializer import (
    AdvertiserPhotoSerializer,
    AdvertiserPropertyDetailSerializer,
    AdvertiserPropertySerializer,
)
from advertiser.modules.property.service import AdvertiserPropertyService
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import Property, PropertyPhoto, PropertyView
from core.modules.property.serializer import (
    PropertyPhotoReorderSerializer,
    PropertyPhotoUploadSerializer,
)

PHOTO_ID_PATTERN = r"(?P<photo_id>[0-9a-fA-F-]{32,36})"
PURPOSE_PRICE_FIELD = {"SALE": "sale_price", "RENT": "rent_price", "SEASONAL": "seasonal_rent_price"}
STATUS_FILTERS = {
    "active": Q(is_active=True, status=Property.Status.PUBLISHED),
    "inactive": Q(is_active=False),
    "draft": Q(status=Property.Status.DRAFT),
}
SLUG_FILTERS = {
    "property_type": "property_type__slug",
    "city": "city__slug",
    "neighborhood": "neighborhood__slug",
}


class AdvertiserPropertyViewSet(CurrentAdvertiserMixin, BaseModelViewSet):
    view_name = "advertiser_property"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = AdvertiserPropertySerializer
    search_fields = ["reference_code", "title", "description"]
    ordering_fields = [
        "reference_code",
        "title",
        "ad_type",
        "sale_price",
        "rent_price",
        "seasonal_rent_price",
        "created_at",
        "updated_at",
    ]
    ordering = ("-updated_at",)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AdvertiserPropertyDetailSerializer
        return AdvertiserPropertySerializer

    def get_queryset(self):
        views = (
            PropertyView.objects.filter(property=OuterRef("pk"))
            .order_by()
            .values("property")
            .annotate(total=Count("id"))
            .values("total")
        )
        queryset = (
            Property.objects.filter(advertiser=self.advertiser, deleted_at__isnull=True)
            .select_related("property_type", "city", "city__state", "neighborhood")
            .prefetch_related(
                Prefetch(
                    "photos", queryset=PropertyPhoto.objects.order_by("sort_order", "created_at")
                ),
                "features",
                "fees",
            )
            .annotate(views_count=Coalesce(Subquery(views, output_field=IntegerField()), 0))
        )
        if self.action == "list":
            queryset = self._apply_list_filters(queryset)
        return queryset

    def _apply_list_filters(self, queryset):
        params = self.request.query_params
        price_field = PURPOSE_PRICE_FIELD.get((params.get("purpose") or "").upper())
        if price_field:
            queryset = queryset.filter(**{f"{price_field}__isnull": False})
        for param, lookup in SLUG_FILTERS.items():
            if params.get(param):
                queryset = queryset.filter(**{lookup: params[param]})
        status_filter = STATUS_FILTERS.get((params.get("status") or "").lower())
        if status_filter is not None:
            queryset = queryset.filter(status_filter)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Cria o imóvel do anunciante logado; a resposta traz o objeto completo

        Returns:
            envelope com o imóvel criado
        """
        response = super().create(request, *args, **kwargs)
        response.data["data"] = self._full_object(response.data["data"]["id"])
        return response

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o imóvel; `features` e `fees` enviados substituem as listas

        Returns:
            envelope com o imóvel atualizado (objeto completo)
        """
        response = super().update(request, *args, **kwargs)
        response.data["data"] = self._full_object(response.data["data"]["id"])
        return response

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    @action(detail=True, methods=["post", "delete"], url_path="photos")
    @transaction.atomic
    def photos(self, request, pk=None):
        """
        POST anexa imagens (`images`, multipart) respeitando o limite do plano; DELETE apaga todas

        Returns:
            envelope com a lista completa de fotos do imóvel
        """
        prop = self.get_object()
        if request.method == "DELETE":
            return self._photos_response(self._service().remove_all_photos(prop))

        serializer = PropertyPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photos = self._service().add_photos(prop, serializer.validated_data["images"])
        return self._photos_response(photos, status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=rf"photos/{PHOTO_ID_PATTERN}")
    @transaction.atomic
    def delete_photo(self, request, pk=None, photo_id=None):
        """
        Remove a foto do imóvel; se era a capa, a próxima assume

        Returns:
            envelope com a lista completa de fotos do imóvel
        """
        photos = self._service().remove_photo(self.get_object(), photo_id)
        return self._photos_response(photos)

    @action(detail=True, methods=["post"], url_path=rf"photos/{PHOTO_ID_PATTERN}/cover")
    @transaction.atomic
    def set_cover_photo(self, request, pk=None, photo_id=None):
        """
        Define a foto como capa única do imóvel

        Returns:
            envelope com a lista completa de fotos do imóvel
        """
        photos = self._service().set_cover(self.get_object(), photo_id)
        return self._photos_response(photos)

    @action(detail=True, methods=["post"], url_path="photos/reorder")
    @transaction.atomic
    def reorder_photos(self, request, pk=None):
        """
        Reordena as fotos conforme `ids` (lista de UUID na nova ordem)

        Returns:
            envelope com a lista completa de fotos do imóvel
        """
        prop = self.get_object()
        serializer = PropertyPhotoReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photos = self._service().reorder_photos(prop, serializer.validated_data["ids"])
        return self._photos_response(photos)

    def _full_object(self, pk):
        instance = self.get_queryset().get(pk=pk)
        return AdvertiserPropertyDetailSerializer(
            instance, context=self.get_serializer_context()
        ).data

    def _photos_response(self, photos, http_status=status.HTTP_200_OK):
        serializer = AdvertiserPhotoSerializer(photos, many=True, context={"request": self.request})
        return envelope_success(data=serializer.data, http_status=http_status)

    def _service(self) -> AdvertiserPropertyService:
        return AdvertiserPropertyService(advertiser=self.advertiser, user=self.request.user)
