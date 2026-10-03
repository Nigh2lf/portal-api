from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import Banner
from core.modules.banner.serializer import (
    BannerDetailSerializer,
    BannerListSerializer,
    BannerSerializer,
)


class BannerViewSet(BaseModelViewSet):
    view_name = "banner"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = BannerSerializer
    search_fields = ["portal__name"]
    filterset_fields = ["portal", "is_active"]
    ordering_fields = ["created_at", "is_active"]
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return BannerListSerializer
        if self.action == "retrieve":
            return BannerDetailSerializer
        return BannerSerializer

    def get_queryset(self):
        return Banner.objects.select_related("portal")
