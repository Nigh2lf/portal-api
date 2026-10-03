from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Ad, AdClick, AdPlacement, Portal
from core.services.public_cache import cached
from public.modules.portal.serializer import (
    PublicAdSerializer,
    PublicBannerSerializer,
    PublicCitySerializer,
    PublicFeatureSerializer,
    PublicNeighborhoodSerializer,
    PublicPortalListSerializer,
    PublicPortalSerializer,
    PublicPropertyCardSerializer,
    PublicPropertyTypeSerializer,
)
from public.modules.portal.service import HomeService
from public.services.scope import cached_portal, portal_queryset

MAX_LIMIT = 50


class PublicPortalViewSet(BaseViewSet):
    # allow-any: consumido pelo site público (SSR), sem usuário logado; throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"
    lookup_field = "slug"
    lookup_value_regex = r"[a-z0-9-]+"

    def get_queryset(self):
        return portal_queryset()

    def get_portal(self, slug):
        portal = cached_portal(slug)
        if portal is None:
            raise NotFound("Portal não encontrado.")
        return portal

    def _portal_payload(self, slug):
        portal = self.get_portal(slug)

        def montar():
            portal.total_properties = HomeService(portal).total_properties()
            return PublicPortalSerializer(portal, context={"request": self.request}).data

        return cached("portal", montar, portal=slug, params={"view": "detail"})

    @staticmethod
    def _slug_by_host(host):
        for portal in Portal.objects.filter(is_active=True).only("slug", "domain", "extra_domains"):
            dominios = {portal.domain.lower(), *(d.lower() for d in portal.extra_domains or [])}
            if host in dominios:
                return portal.slug
        return None

    def _limit(self, default, maximo=MAX_LIMIT):
        try:
            valor = int(self.request.query_params.get("limit", default))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"limit": ["Informe um número."]}) from exc
        return max(1, min(valor, maximo))

    def list(self, request):
        """
        Lista os portais ativos (slug, nome, domínio)

        Returns:
            envelope com `[{id, slug, name, domain}]`
        """
        dados = cached("portal", lambda: PublicPortalListSerializer(Portal.objects.filter(is_active=True), many=True).data, params={"view": "list"})
        return envelope_success(data=dados)

    def retrieve(self, request, slug=None):
        """
        Configuração completa do portal pelo slug

        Returns:
            envelope com os dados do portal e `total_properties`
        """
        return envelope_success(data=self._portal_payload(slug))

    @action(detail=False, methods=["get"], url_path="by-host")
    def by_host(self, request):
        """
        Resolve o portal pelo host da requisição do site (`?host=www.exemplo.com.br`)

        Returns:
            envelope com os mesmos dados do retrieve; 404 se nenhum domínio casar
        """
        host = (request.query_params.get("host") or "").lower().split(":")[0]
        if not host:
            raise ValidationError({"host": ["Informe o host."]})
        slug = cached("portal", lambda: self._slug_by_host(host), params={"view": "by-host", "host": host})
        if slug is None:
            raise NotFound("Nenhum portal para este host.")
        return envelope_success(data=self._portal_payload(slug))

    @action(detail=True, methods=["get"], url_path="featured-properties")
    def featured_properties(self, request, slug=None):
        """
        Imóveis em destaque do portal (`?limit=`, padrão 12)

        Returns:
            envelope com cards de imóvel
        """
        portal = self.get_portal(slug)
        limit = self._limit(12)
        dados = cached(
            "home",
            lambda: PublicPropertyCardSerializer(HomeService(portal).featured(limit=limit), many=True, context={"request": request}).data,
            portal=slug,
            params={"view": "featured", "limit": limit},
        )
        return envelope_success(data=dados)

    @action(detail=True, methods=["get"], url_path="top-searches")
    def top_searches(self, request, slug=None):
        """
        Imóveis mais procurados: combinações objetivo + tipo + bairro (`?limit=`, padrão 15)

        Returns:
            envelope com `[{purpose, property_type, city, neighborhood, total}]`
        """
        portal = self.get_portal(slug)
        limit = self._limit(15)
        dados = cached("home", lambda: HomeService(portal).top_searches(limit=limit), portal=slug, params={"view": "top-searches", "limit": limit})
        return envelope_success(data=dados)

    @action(detail=True, methods=["get"], url_path="top-neighborhoods")
    def top_neighborhoods(self, request, slug=None):
        """
        Bairros mais anunciados (`?limit=`, padrão 15)

        Returns:
            envelope com `[{neighborhood, city, total}]`
        """
        portal = self.get_portal(slug)
        limit = self._limit(15)
        dados = cached("home", lambda: HomeService(portal).top_neighborhoods(limit=limit), portal=slug, params={"view": "top-neighborhoods", "limit": limit})
        return envelope_success(data=dados)

    @action(detail=True, methods=["get"], url_path="banners")
    def banners(self, request, slug=None):
        """
        Banners ativos do hero (do portal ou globais)

        Returns:
            envelope com `[{id, home_image_url, inner_image_url}]`
        """
        portal = self.get_portal(slug)
        dados = cached(
            "content",
            lambda: PublicBannerSerializer(HomeService(portal).banners(), many=True, context={"request": request}).data,
            portal=slug,
            params={"view": "banners"},
        )
        return envelope_success(data=dados)

    @action(detail=True, methods=["get"], url_path="ads")
    def ads(self, request, slug=None):
        """
        Anúncios publicitários vigentes (`?page=HOME|SEARCH|PROPERTY`, `?kind=POPUP|HORIZONTAL|SIDEBAR`)

        Returns:
            envelope com `[{id, name, image_url, link_url, open_in_new_tab, placement_*}]`
        """
        portal = self.get_portal(slug)
        page = request.query_params.get("page") or None
        kind = request.query_params.get("kind") or None
        if page and page not in AdPlacement.Page.values:
            raise ValidationError({"page": ["Valor inválido."]})
        if kind and kind not in AdPlacement.Kind.values:
            raise ValidationError({"kind": ["Valor inválido."]})
        dados = cached(
            "content",
            lambda: PublicAdSerializer(HomeService(portal).ads(page=page, kind=kind), many=True, context={"request": request}).data,
            portal=slug,
            params={"view": "ads", "page": page, "kind": kind},
        )
        return envelope_success(data=dados)

    @action(detail=True, methods=["get"], url_path="ads/(?P<ad_id>[0-9a-f-]{36})/click")
    def ad_click(self, request, slug=None, ad_id=None):
        """
        Registra o clique no anúncio e devolve o link de destino

        Returns:
            envelope com `{link_url, open_in_new_tab}`
        """
        portal = self.get_portal(slug)
        ad = Ad.objects.filter(pk=ad_id, portal=portal).first()
        if ad is None:
            raise NotFound("Anúncio não encontrado.")
        AdClick.objects.create(ad=ad, ip_address=request.META.get("REMOTE_ADDR"), referer=request.META.get("HTTP_REFERER", "")[:2000])
        return envelope_success(data={"link_url": ad.link_url, "open_in_new_tab": ad.open_in_new_tab})

    @action(detail=True, methods=["get"], url_path="catalog")
    def catalog(self, request, slug=None):
        """
        Opções do formulário de busca: tipos, cidades do portal, bairros com anúncios e características

        Returns:
            envelope com `{property_types, cities, neighborhoods: [{..., total}], features}`
        """
        portal = self.get_portal(slug)
        return envelope_success(data=cached("catalog", lambda: self._catalog_payload(portal), portal=slug, params={"view": "catalog"}))

    @staticmethod
    def _catalog_payload(portal):
        dados = HomeService(portal).catalog()
        bairros = []
        for bairro, total in dados["neighborhoods"]:
            item = PublicNeighborhoodSerializer(bairro).data
            item["total"] = total
            bairros.append(item)
        return {
            "property_types": PublicPropertyTypeSerializer(dados["property_types"], many=True).data,
            "cities": PublicCitySerializer(dados["cities"], many=True).data,
            "neighborhoods": bairros,
            "features": PublicFeatureSerializer(dados["features"], many=True).data,
        }
