from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Integrator
from core.modules.integrator.serializer import (
    IntegratorDetailSerializer,
    IntegratorListSerializer,
    IntegratorSerializer,
)


class IntegratorViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "integrator"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = IntegratorSerializer
    search_fields = ["name", "slug"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "slug", "created_at"]
    ordering = ("name",)

    def get_serializer_class(self):
        if self.action == "list":
            return IntegratorListSerializer
        if self.action == "retrieve":
            return IntegratorDetailSerializer
        return IntegratorSerializer

    def get_queryset(self):
        return Integrator.objects.all()
