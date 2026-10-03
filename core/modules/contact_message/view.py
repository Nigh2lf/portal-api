from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import ContactMessage
from core.modules.contact_message.serializer import (
    ContactMessageDetailSerializer,
    ContactMessageListSerializer,
)


class ContactMessageViewSet(BaseModelViewSet):
    view_name = "contact_message"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = ContactMessageDetailSerializer
    search_fields = ["name", "email", "phone", "subject", "message"]
    filterset_fields = {"portal": ["exact"], "created_at": ["gte", "lte"]}
    ordering_fields = ["name", "email", "subject", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return ContactMessageListSerializer
        return ContactMessageDetailSerializer

    def get_queryset(self):
        return ContactMessage.objects.select_related("portal")
