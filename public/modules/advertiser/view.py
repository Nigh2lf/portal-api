import random

from django.db.models import Count, Q
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Advertiser
from core.services.public_cache import cached
from public.modules.property.serializer import PublicAdvertiserSerializer
from public.services.scope import cached_portal, property_visibility_q, visible_advertisers


class PublicAdvertiserViewSet(BaseViewSet):
    # allow-any: diretório de imobiliárias e hotsite do site público; sem login, throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"
    lookup_field = "slug"
    lookup_value_regex = r"[a-z0-9-]+"

    def get_portal(self):
        portal = cached_portal(self.kwargs.get("portal_slug"))
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

        def montar():
            itens = list(self._with_totals(visible_advertisers(portal).filter(has_realtor_page=True), portal))
            ctx = {"request": request}
            return {
                "agencies": list(PublicAdvertiserSerializer([a for a in itens if a.type == Advertiser.Type.AGENCY], many=True, context=ctx).data),
                "brokers": list(PublicAdvertiserSerializer([a for a in itens if a.type == Advertiser.Type.BROKER], many=True, context=ctx).data),
            }

        dados = cached("advertiser", montar, portal=portal.slug, params={"view": "list"})
        # A ordem aleatória (rodízio entre anunciantes) é aplicada a cada requisição, fora do cache.
        random.shuffle(dados["agencies"])
        random.shuffle(dados["brokers"])
        return envelope_success(data=dados)

    def retrieve(self, request, portal_slug=None, slug=None):
        """
        Dados do hotsite de um anunciante (exige `has_hotsite`)

        Returns:
            envelope com o bloco público do anunciante e totais por objetivo
        """
        portal = self.get_portal()

        def montar():
            a = self._with_totals(visible_advertisers(portal).filter(slug=slug, has_hotsite=True), portal).first()
            if a is None:
                raise NotFound("Anunciante não encontrado.")
            return PublicAdvertiserSerializer(a, context={"request": request}).data

        return envelope_success(data=cached("advertiser", montar, portal=portal.slug, params={"view": "detail", "slug": slug}))
