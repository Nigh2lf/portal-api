from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Portal, PortalMenuItem
from core.modules.portal.serializer import (
    PortalDetailSerializer,
    PortalListSerializer,
    PortalSerializer,
)
from core.modules.portal.service import PortalService


class PortalViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "portal"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = PortalSerializer
    search_fields = ["name", "slug", "domain"]
    filterset_fields = ["is_active", "main_city"]
    ordering_fields = ["name", "slug", "domain", "created_at"]
    ordering = ("name",)

    def get_serializer_class(self):
        if self.action == "list":
            return PortalListSerializer
        if self.action == "retrieve":
            return PortalDetailSerializer
        return PortalSerializer

    def get_queryset(self):
        queryset = Portal.objects.select_related("main_city")
        if self.action == "list":
            return queryset
        return queryset.prefetch_related(
            "cities",
            "combined_portals",
            Prefetch("menu_items", queryset=PortalMenuItem.objects.order_by("sort_order")),
        )

    def create(self, request, *args, **kwargs):
        """
        Cria o portal com cidades, portais combinados e itens de menu

        Returns:
            envelope com os dados do portal criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o portal; listas aninhadas enviadas substituem as atuais

        Returns:
            envelope com os dados do portal atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> PortalService:
        return PortalService(user=self.request.user)
