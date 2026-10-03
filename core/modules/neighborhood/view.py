from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Neighborhood
from core.modules.neighborhood.serializer import (
    NeighborhoodDetailSerializer,
    NeighborhoodListSerializer,
    NeighborhoodSerializer,
)
from core.modules.neighborhood.service import NeighborhoodService


class NeighborhoodViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "neighborhood"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = NeighborhoodSerializer
    search_fields = ["name", "slug", "city__name"]
    filterset_fields = ["city", "city__state", "is_active"]
    ordering_fields = ["name", "slug", "created_at", "city__name"]
    ordering = ("name",)

    def get_serializer_class(self):
        if self.action == "list":
            return NeighborhoodListSerializer
        if self.action == "retrieve":
            return NeighborhoodDetailSerializer
        return NeighborhoodSerializer

    def get_queryset(self):
        return Neighborhood.objects.select_related("city", "city__state")

    def create(self, request, *args, **kwargs):
        """
        Cria o bairro; `slug` ausente é gerado a partir de `name`

        Returns:
            envelope com os dados do bairro criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o bairro; `slug` vazio é regenerado

        Returns:
            envelope com os dados do bairro atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> NeighborhoodService:
        return NeighborhoodService(user=self.request.user)
