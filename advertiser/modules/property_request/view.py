from rest_framework.permissions import IsAuthenticated

from advertiser.modules.property_request.serializer import AdvertiserPropertyRequestSerializer
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import PropertyRequest


class AdvertiserPropertyRequestViewSet(CurrentAdvertiserMixin, BaseModelViewSet):
    view_name = "advertiser_property_request"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "head", "options"]
    serializer_class = AdvertiserPropertyRequestSerializer
    search_fields = ["name", "email", "phone", "message"]
    filterset_fields = {"purpose": ["exact"], "created_at": ["gte", "lte"]}
    ordering_fields = ["name", "created_at"]
    ordering = ("-created_at",)

    def get_queryset(self):
        advertiser = self.advertiser
        if not advertiser.receives_property_requests:
            return PropertyRequest.objects.none()
        return PropertyRequest.objects.filter(
            is_partner_broadcast=True, portal_id=advertiser.portal_id
        ).select_related("property_type", "city", "neighborhood")
