from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import AdPlacement, Plan
from core.services.public_cache import cached
from public.modules.plan.serializer import PublicAdPlacementSerializer, PublicPlanSerializer


class PublicPlanViewSet(BaseViewSet):
    # allow-any: tabela de planos exibida na página "Anunciar" do site público; sem login, throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def list(self, request):
        """
        Planos ativos, na ordem de exibição

        Returns:
            envelope com `[{id, slug, name, monthly_price, property_limit, ...}]`
        """
        dados = cached("plans", lambda: PublicPlanSerializer(Plan.objects.filter(is_active=True).order_by("sort_order", "name"), many=True).data, params={"view": "plans"})
        return envelope_success(data=dados)


class PublicAdPlacementViewSet(BaseViewSet):
    # allow-any: tabela de preços de publicidade do site público; sem login, throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def list(self, request):
        """
        Espaços publicitários ativos (tabela de publicidade)

        Returns:
            envelope com `[{code, name, page, kind, width, height, monthly_price, notes}]`
        """
        dados = cached("plans", lambda: PublicAdPlacementSerializer(AdPlacement.objects.filter(is_active=True).order_by("code"), many=True).data, params={"view": "ad-placements"})
        return envelope_success(data=dados)
