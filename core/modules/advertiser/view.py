from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Advertiser
from core.modules.advertiser.serializer import (
    AdvertiserDetailSerializer,
    AdvertiserListSerializer,
    AdvertiserSerializer,
)
from core.modules.advertiser.service import AdvertiserService


class AdvertiserViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "advertiser"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = AdvertiserSerializer
    search_fields = ["name", "slug", "email", "document", "contact_name"]
    filterset_fields = ["portal", "plan", "type", "is_published", "has_hotsite"]
    ordering_fields = ["name", "slug", "type", "email", "is_published", "created_at"]
    ordering = ("name",)

    def get_serializer_class(self):
        if self.action == "list":
            return AdvertiserListSerializer
        if self.action == "retrieve":
            return AdvertiserDetailSerializer
        return AdvertiserSerializer

    def get_queryset(self):
        queryset = (
            Advertiser.objects.filter(deleted_at__isnull=True)
            .select_related("plan", "portal")
            .annotate(
                properties_count=Count(
                    "properties", filter=Q(properties__deleted_at__isnull=True), distinct=True
                )
            )
        )
        if self.action in ("list", "options_list"):
            return queryset
        return queryset.select_related(
            "user", "integration", "integration__integrator"
        ).prefetch_related("advertiser_cities")

    def create(self, request, *args, **kwargs):
        """
        Cria o anunciante com integração e cidades; `slug` ausente é gerado de `name`

        Returns:
            envelope com os dados do anunciante criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o anunciante; `integration` faz upsert e `cities` substitui a lista

        Returns:
            envelope com os dados do anunciante atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Totais de anunciantes para o painel inicial

        Returns:
            envelope com os contadores (ver docs/index.md)
        """
        return envelope_success(data=AdvertiserService.summary())

    def _service(self) -> AdvertiserService:
        return AdvertiserService(user=self.request.user)
