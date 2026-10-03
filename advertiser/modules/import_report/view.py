from rest_framework.permissions import IsAuthenticated

from advertiser.modules.import_report.service import build_import_report
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass


class AdvertiserImportReportViewSet(CurrentAdvertiserMixin, BaseViewSet):
    view_name = "advertiser_import"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]

    def list(self, request):
        """
        Relatório da última importação XML (totais, rejeitados e erros)

        Returns:
            envelope com o relatório; 404 se o anunciante não tem integração XML
        """
        return envelope_success(data=build_import_report(self.advertiser))
