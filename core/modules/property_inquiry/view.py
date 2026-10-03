from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import PropertyInquiry
from core.modules.property_inquiry.serializer import (
    PropertyInquiryDetailSerializer,
    PropertyInquiryListSerializer,
)


class PropertyInquiryViewSet(BaseModelViewSet):
    view_name = "property_inquiry"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = PropertyInquiryDetailSerializer
    search_fields = ["name", "email", "phone", "property_reference_code", "message"]
    filterset_fields = {
        "advertiser": ["exact"],
        "portal": ["exact"],
        "property": ["exact"],
        "is_mobile": ["exact"],
        "created_at": ["gte", "lte"],
    }
    ordering_fields = ["name", "email", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyInquiryListSerializer
        return PropertyInquiryDetailSerializer

    def get_queryset(self):
        queryset = PropertyInquiry.objects.select_related("advertiser", "portal")
        if self.action == "list":
            return queryset
        return queryset.select_related("property")
