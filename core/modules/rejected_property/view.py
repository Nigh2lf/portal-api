from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import RejectedProperty
from core.modules.rejected_property.serializer import (
    RejectedPropertyDetailSerializer,
    RejectedPropertyListSerializer,
    RejectedPropertySerializer,
)


class RejectedPropertyViewSet(BaseModelViewSet):
    view_name = "rejected_property"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = RejectedPropertySerializer
    search_fields = ["property_reference_code", "reason", "advertiser__name"]
    filterset_fields = ["advertiser"]
    ordering_fields = ["property_reference_code", "created_at", "advertiser__name"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return RejectedPropertyListSerializer
        if self.action == "retrieve":
            return RejectedPropertyDetailSerializer
        return RejectedPropertySerializer

    def get_queryset(self):
        return RejectedProperty.objects.select_related("advertiser")
