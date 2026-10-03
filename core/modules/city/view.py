from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import City
from core.modules.city.serializer import (
    CityDetailSerializer,
    CityListSerializer,
    CitySerializer,
)
from core.modules.city.service import CityService


class CityViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "city"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = CitySerializer
    search_fields = ["name", "slug", "state__code"]
    filterset_fields = ["state", "is_active"]
    ordering_fields = ["name", "slug", "created_at", "state__code"]
    ordering = ("name",)

    def get_serializer_class(self):
        if self.action == "list":
            return CityListSerializer
        if self.action == "retrieve":
            return CityDetailSerializer
        return CitySerializer

    def get_queryset(self):
        return City.objects.select_related("state")

    def create(self, request, *args, **kwargs):
        """
        Cria a cidade; `slug` ausente é gerado a partir de `name`

        Returns:
            envelope com os dados da cidade criada
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza a cidade; `slug` vazio é regenerado

        Returns:
            envelope com os dados da cidade atualizada
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> CityService:
        return CityService(user=self.request.user)
