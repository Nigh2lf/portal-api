from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.lookup_options import LookupOptionsMixin
from core.classes.permission import CustomPermissionClass
from core.models import State
from core.modules.state.serializer import (
    StateDetailSerializer,
    StateListSerializer,
    StateSerializer,
)


class StateViewSet(LookupOptionsMixin, BaseModelViewSet):
    view_name = "state"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = StateSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["code"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ("code",)

    def get_serializer_class(self):
        if self.action == "list":
            return StateListSerializer
        if self.action == "retrieve":
            return StateDetailSerializer
        return StateSerializer

    def get_queryset(self):
        return State.objects.all()
