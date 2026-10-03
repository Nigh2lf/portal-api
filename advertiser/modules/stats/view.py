from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from advertiser.modules.stats.serializer import (
    MonthlyStatsQuerySerializer,
    PeriodStatsQuerySerializer,
)
from advertiser.modules.stats.service import AdvertiserStatsService
from advertiser.modules.stats.service.stats_service import STATS_TZ
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass


class AdvertiserStatsViewSet(CurrentAdvertiserMixin, BaseViewSet):
    view_name = "advertiser_stats"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]

    @action(detail=False, methods=["get"])
    def monthly(self, request):
        """
        Estatísticas dos últimos `months` meses (default 3), do mais recente para o mais antigo

        Returns:
            envelope com a lista mensal
        """
        query = MonthlyStatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return envelope_success(data=self._service().monthly(query.validated_data["months"]))

    @action(detail=False, methods=["get"])
    def period(self, request):
        """
        Estatísticas entre `start` e `end` (default: mês atual) com ranking por imóvel

        Returns:
            envelope com os totais do período e `by_property`
        """
        query = PeriodStatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        today = timezone.now().astimezone(STATS_TZ).date()
        start = query.validated_data.get("start") or today.replace(day=1)
        end = query.validated_data.get("end") or max(today, start)
        return envelope_success(data=self._service().period(start, end))

    def _service(self) -> AdvertiserStatsService:
        return AdvertiserStatsService(advertiser=self.advertiser)
