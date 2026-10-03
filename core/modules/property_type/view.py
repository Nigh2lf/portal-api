from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import PropertyType
from core.modules.property_type.serializer import (
    PropertyTypeDetailSerializer,
    PropertyTypeListSerializer,
    PropertyTypeSerializer,
)
from core.modules.property_type.service import PropertyTypeService


class PropertyTypeViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "property_type"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = PropertyTypeSerializer
    search_fields = ["name", "slug"]
    filterset_fields = ["is_active", "is_residential"]
    ordering_fields = ["sort_order", "name", "slug", "created_at"]
    ordering = ("sort_order", "name")

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyTypeListSerializer
        if self.action == "retrieve":
            return PropertyTypeDetailSerializer
        return PropertyTypeSerializer

    def get_queryset(self):
        return PropertyType.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Cria o tipo de imóvel; `slug` ausente é gerado a partir de `name`

        Returns:
            envelope com os dados do tipo criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o tipo de imóvel; `slug` vazio é regenerado

        Returns:
            envelope com os dados do tipo atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> PropertyTypeService:
        return PropertyTypeService(user=self.request.user)
