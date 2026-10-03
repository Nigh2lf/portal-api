from django_filters import rest_framework as filters
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import AdPlacement
from core.modules.ad_placement.serializer import (
    AdPlacementDetailSerializer,
    AdPlacementListSerializer,
    AdPlacementSerializer,
)


class AdPlacementFilter(filters.FilterSet):
    page_type = filters.ChoiceFilter(field_name="page", choices=AdPlacement.Page.choices)

    class Meta:
        model = AdPlacement
        fields = ["page_type", "kind", "is_active"]


class AdPlacementViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "ad_placement"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = AdPlacementSerializer
    search_fields = ["code", "name"]
    filterset_class = AdPlacementFilter
    ordering_fields = ["code", "name", "page", "kind", "monthly_price", "created_at"]
    ordering = ("code",)

    def get_serializer_class(self):
        if self.action == "list":
            return AdPlacementListSerializer
        if self.action == "retrieve":
            return AdPlacementDetailSerializer
        return AdPlacementSerializer

    def get_queryset(self):
        return AdPlacement.objects.all()
