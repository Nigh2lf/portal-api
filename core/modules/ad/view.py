from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import Ad
from core.modules.ad.serializer import AdDetailSerializer, AdListSerializer, AdSerializer


class AdViewSet(BaseModelViewSet):
    view_name = "ad"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = AdSerializer
    search_fields = ["name", "link_url", "portal__name"]
    filterset_fields = ["portal", "placement", "is_active"]
    ordering_fields = ["name", "starts_at", "ends_at", "is_active", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return AdListSerializer
        if self.action == "retrieve":
            return AdDetailSerializer
        return AdSerializer

    def get_queryset(self):
        return Ad.objects.select_related("portal", "placement")
