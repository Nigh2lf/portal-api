from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import Plan
from core.modules.plan.serializer import (
    PlanDetailSerializer,
    PlanListSerializer,
    PlanSerializer,
)


class PlanViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "plan"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = PlanSerializer
    search_fields = ["name", "slug"]
    filterset_fields = ["is_active", "is_recommended", "is_owner_only"]
    ordering_fields = ["sort_order", "name", "monthly_price", "created_at"]
    ordering = ("sort_order", "name")

    def get_serializer_class(self):
        if self.action == "list":
            return PlanListSerializer
        if self.action == "retrieve":
            return PlanDetailSerializer
        return PlanSerializer

    def get_queryset(self):
        return Plan.objects.all()
