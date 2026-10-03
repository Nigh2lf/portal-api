from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import PropertyRequest
from core.modules.property_request.serializer import (
    PropertyRequestDetailSerializer,
    PropertyRequestListSerializer,
)


class PropertyRequestViewSet(BaseModelViewSet):
    view_name = "property_request"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = PropertyRequestDetailSerializer
    search_fields = ["name", "email", "phone", "message"]
    filterset_fields = {
        "portal": ["exact"],
        "advertiser": ["exact"],
        "purpose": ["exact"],
        "property_type": ["exact"],
        "city": ["exact"],
        "neighborhood": ["exact"],
        "is_partner_broadcast": ["exact"],
        "created_at": ["gte", "lte"],
    }
    ordering_fields = ["name", "email", "purpose", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyRequestListSerializer
        return PropertyRequestDetailSerializer

    def get_queryset(self):
        return PropertyRequest.objects.select_related(
            "portal", "advertiser", "property_type", "city", "neighborhood"
        )
