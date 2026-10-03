from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import BlockedSender
from core.modules.blocked_sender.serializer import (
    BlockedSenderDetailSerializer,
    BlockedSenderListSerializer,
    BlockedSenderSerializer,
)


class BlockedSenderViewSet(BaseModelViewSet):
    view_name = "blocked_sender"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = BlockedSenderSerializer
    search_fields = ["email", "ip_address", "reason"]
    filterset_fields = ["is_active"]
    ordering_fields = ["email", "ip_address", "is_active", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return BlockedSenderListSerializer
        if self.action == "retrieve":
            return BlockedSenderDetailSerializer
        return BlockedSenderSerializer

    def get_queryset(self):
        return BlockedSender.objects.all()
