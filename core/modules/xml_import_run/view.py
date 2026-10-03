from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import XmlImportError, XmlImportRun
from core.modules.xml_import_run.serializer import (
    XmlImportRunDetailSerializer,
    XmlImportRunListSerializer,
)


class XmlImportRunViewSet(BaseModelViewSet):
    view_name = "xml_import_run"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = XmlImportRunDetailSerializer
    search_fields = ["advertiser__name"]
    filterset_fields = {
        "advertiser": ["exact"],
        "report_email_sent": ["exact"],
        "started_at": ["gte", "lte"],
    }
    ordering_fields = ["started_at", "finished_at", "total_properties", "invalid_properties"]
    ordering = ("-started_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return XmlImportRunListSerializer
        return XmlImportRunDetailSerializer

    def get_queryset(self):
        queryset = XmlImportRun.objects.select_related("advertiser")
        if self.action == "list":
            return queryset
        return queryset.prefetch_related(
            Prefetch("errors", queryset=XmlImportError.objects.order_by("created_at"))
        )
