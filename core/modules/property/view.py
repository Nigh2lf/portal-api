from django.db import transaction
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import Property, PropertyPhoto
from core.modules.property.serializer import (
    PropertyDetailSerializer,
    PropertyListSerializer,
    PropertyPhotoReorderSerializer,
    PropertyPhotoSerializer,
    PropertyPhotoUploadSerializer,
    PropertySerializer,
)
from core.modules.property.service import PropertyService

PHOTO_ID_PATTERN = r"(?P<photo_id>[0-9a-fA-F-]{32,36})"


class PropertyViewSet(BaseModelViewSet):
    view_name = "property"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = PropertySerializer
    search_fields = ["reference_code", "title", "description"]
    filterset_fields = [
        "advertiser",
        "advertiser__portal",
        "property_type",
        "city",
        "neighborhood",
        "status",
        "is_active",
        "ad_type",
    ]
    ordering_fields = [
        "reference_code",
        "title",
        "status",
        "ad_type",
        "sale_price",
        "rent_price",
        "seasonal_rent_price",
        "created_at",
        "updated_at",
    ]
    ordering = ("-updated_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyListSerializer
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertySerializer

    def get_queryset(self):
        queryset = Property.objects.filter(deleted_at__isnull=True).select_related(
            "advertiser", "property_type", "city", "city__state", "neighborhood"
        )
        photos = PropertyPhoto.objects.order_by("sort_order")
        if self.action == "list":
            return queryset.prefetch_related(
                Prefetch("photos", queryset=photos.filter(is_cover=True))
            )
        return queryset.prefetch_related(Prefetch("photos", queryset=photos), "features", "fees")

    def create(self, request, *args, **kwargs):
        """
        Cria o imóvel com características e taxas; título/slug gerados quando ausentes

        Returns:
            envelope com os dados do imóvel criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o imóvel; `features` e `fees` enviados substituem as listas

        Returns:
            envelope com os dados do imóvel atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    @action(detail=True, methods=["post"], url_path="photos")
    @transaction.atomic
    def upload_photos(self, request, pk=None):
        """
        Anexa uma ou mais imagens (`images`, multipart) ao imóvel

        Returns:
            envelope com a lista completa de fotos do imóvel
        """
        prop = self.get_object()
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

    def _photos_response(self, photos, http_status=status.HTTP_200_OK):
        serializer = PropertyPhotoSerializer(photos, many=True, context={"request": self.request})
        return envelope_success(data=serializer.data, http_status=http_status)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Totais de imóveis para o painel inicial

        Returns:
            envelope com os contadores (ver docs/index.md)
        """
        return envelope_success(data=PropertyService.summary())

    def _service(self) -> PropertyService:
        return PropertyService(user=self.request.user)
