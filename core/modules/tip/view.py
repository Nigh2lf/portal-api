from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import Tip
from core.modules.tip.serializer import TipDetailSerializer, TipListSerializer, TipSerializer


class TipViewSet(BaseModelViewSet):
    view_name = "tip"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = TipSerializer
    search_fields = ["title", "body"]
    filterset_fields = ["portal", "is_active"]
    ordering_fields = ["sort_order", "title", "published_at", "created_at"]
    ordering = ("sort_order", "-published_at")

    def get_serializer_class(self):
        if self.action == "list":
            return TipListSerializer
        if self.action == "retrieve":
            return TipDetailSerializer
        return TipSerializer

    def get_queryset(self):
        return Tip.objects.select_related("portal")
