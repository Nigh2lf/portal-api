from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Feature
from core.modules.feature.serializer import (
    FeatureDetailSerializer,
    FeatureListSerializer,
    FeatureSerializer,
)
from core.modules.feature.service import FeatureService


class FeatureViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "feature"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = FeatureSerializer
    search_fields = ["name", "slug"]
    filterset_fields = ["scope", "is_active"]
    ordering_fields = ["scope", "sort_order", "name", "created_at"]
    ordering = ("scope", "sort_order", "name")

    def get_serializer_class(self):
        if self.action == "list":
            return FeatureListSerializer
        if self.action == "retrieve":
            return FeatureDetailSerializer
        return FeatureSerializer

    def get_queryset(self):
        return Feature.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Cria a característica; `slug` ausente é gerado a partir de `name`

        Returns:
            envelope com os dados da característica criada
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza a característica; `slug` vazio é regenerado

        Returns:
            envelope com os dados da característica atualizada
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> FeatureService:
        return FeatureService(user=self.request.user)
