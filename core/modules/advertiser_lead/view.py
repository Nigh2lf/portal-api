from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import AdvertiserLead
from core.modules.advertiser_lead.serializer import (
    AdvertiserLeadDetailSerializer,
    AdvertiserLeadListSerializer,
)


class AdvertiserLeadViewSet(BaseModelViewSet):
    view_name = "advertiser_lead"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = AdvertiserLeadDetailSerializer
    search_fields = ["name", "email", "phone", "company", "message"]
    filterset_fields = {"portal": ["exact"], "created_at": ["gte", "lte"]}
    ordering_fields = ["name", "email", "company", "created_at"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return AdvertiserLeadListSerializer
        return AdvertiserLeadDetailSerializer

    def get_queryset(self):
        return AdvertiserLead.objects.select_related("portal")
