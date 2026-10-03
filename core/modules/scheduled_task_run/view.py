from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import ScheduledTaskRun
from core.modules.scheduled_task_run.serializer import (
    ScheduledTaskRunDetailSerializer,
    ScheduledTaskRunListSerializer,
)


class ScheduledTaskRunViewSet(BaseModelViewSet):
    view_name = "scheduled_task_run"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = ScheduledTaskRunDetailSerializer
    search_fields = ["name", "details"]
    filterset_fields = {
        "name": ["exact"],
        "status": ["exact"],
        "started_at": ["gte", "lte"],
    }
    ordering_fields = ["name", "status", "started_at", "finished_at"]
    ordering = ("-started_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return ScheduledTaskRunListSerializer
        return ScheduledTaskRunDetailSerializer

    def get_queryset(self):
        return ScheduledTaskRun.objects.all()
