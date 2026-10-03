from django.db.models import Count, Q
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Advertiser, Portal
from public.modules.property.serializer import PublicAdvertiserSerializer
from public.services.scope import property_visibility_q, visible_advertisers


class PublicAdvertiserViewSet(BaseViewSet):
    # allow-any: diretório de imobiliárias e hotsite do site público; sem login, throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"
    lookup_field = "slug"
    lookup_value_regex = r"[a-z0-9-]+"

    def get_portal(self):
        portal = Portal.objects.filter(slug=self.kwargs.get("portal_slug"), is_active=True).first()
        if portal is None:
            raise NotFound("Portal não encontrado.")
        return portal

    def _with_totals(self, queryset, portal):
        vis = property_visibility_q(portal)
        return queryset.annotate(
            total_properties=Count("properties", filter=vis, distinct=True),
            total_sale=Count("properties", filter=vis & Q(properties__sale_price__isnull=False), distinct=True),
            total_rent=Count("properties", filter=vis & Q(properties__rent_price__isnull=False), distinct=True),
            total_seasonal=Count("properties", filter=vis & Q(properties__seasonal_rent_price__isnull=False), distinct=True),
        )

    def list(self, request, portal_slug=None):
        """
        Diretório de imobiliárias e corretores com página no portal, em ordem aleatória

        Returns:
            envelope com `{agencies: [...], brokers: [...]}`
        """
        portal = self.get_portal()
        qs = self._with_totals(visible_advertisers(portal).filter(has_realtor_page=True), portal).order_by("?")
        itens = list(qs)
        ctx = {"request": request}
        return envelope_success(
            data={
                "agencies": PublicAdvertiserSerializer([a for a in itens if a.type == Advertiser.Type.AGENCY], many=True, context=ctx).data,
                "brokers": PublicAdvertiserSerializer([a for a in itens if a.type == Advertiser.Type.BROKER], many=True, context=ctx).data,
            }
        )

    def retrieve(self, request, portal_slug=None, slug=None):
        """
        Dados do hotsite de um anunciante (exige `has_hotsite`)

        Returns:
            envelope com o bloco público do anunciante e totais por objetivo
        """
        portal = self.get_portal()
        a = self._with_totals(visible_advertisers(portal).filter(slug=slug, has_hotsite=True), portal).first()
        if a is None:
            raise NotFound("Anunciante não encontrado.")
        return envelope_success(data=PublicAdvertiserSerializer(a, context={"request": request}).data)
