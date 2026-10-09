from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Advertiser, Property, PropertyContactClick, PropertyInquiry, PropertyView
from core.services.deferred_writes import defer
from core.services.public_cache import cached
from public.modules.portal.serializer import PublicPropertyCardSerializer
from public.modules.property.serializer import (
    PublicContactClickSerializer,
    PublicInquirySerializer,
    PublicPropertyDetailSerializer,
    PublicSearchResultSerializer,
)
from public.modules.property.service import PURPOSE_PRICE_FIELD, SearchFilters, SearchService
from public.services.scope import attach_advertiser_totals, cached_portal, visible_properties, with_card_data
from public.services.sender import client_ip, ensure_sender_allowed

MAX_IDS = 100


def is_mobile(request):
    return "Mobile" in (request.META.get("HTTP_USER_AGENT") or "")


class PublicPropertyViewSet(BaseViewSet):
    # allow-any: busca e detalhe do site público; sem login, throttle por IP.
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

    def list(self, request, portal_slug=None):
        """
        Busca de imóveis do portal com filtros, abas por objetivo e paginação

        Returns:
            envelope com `{results, count, page, page_size, total_pages, counters, max_price, applied}`
        """
        portal = self.get_portal()
        filters = SearchFilters.from_query(request.query_params, default_page_size=portal.results_per_page or 30)
        service = SearchService(portal)
        params = {k: request.query_params.getlist(k) for k in sorted(request.query_params) if k != "track"}

        def montar():
            resultado = service.search(filters)
            return {"data": PublicSearchResultSerializer(resultado, context={"request": request}).data, "applied": resultado["applied"]}

        r = cached("listing", montar, portal=portal.slug, params={"view": "search", **params})
        if request.query_params.get("track", "1") != "0":
            service.log(filters, r["applied"], request)
        return envelope_success(data=r["data"])

    def retrieve(self, request, portal_slug=None, slug=None):
        """
        Detalhe do imóvel (por slug ou código) com anunciante, relacionados e links (`?related=0` omite os relacionados)

        Returns:
            envelope com `{property, related, related_links}`; 404 se não visível no portal
        """
        portal = self.get_portal()
        chave = (slug or "").lower()
        com_relacionados = request.query_params.get("related", "1") != "0"
        r = cached(
            "listing",
            lambda: self._detail_payload(portal, slug, com_relacionados),
            portal=portal.slug,
            item=chave,
            params={"view": "detail", "related": com_relacionados},
        )
        if request.query_params.get("track", "1") != "0":
            defer(
                PropertyView.objects.create,
                property_id=r["track"]["property_id"],
                property_reference_code=r["track"]["reference_code"],
                advertiser_id=r["track"]["advertiser_id"],
                portal=portal,
                ip_address=client_ip(request),
                referer=(request.META.get("HTTP_REFERER") or "")[:2000],
                is_mobile=is_mobile(request),
            )
        return envelope_success(data=r["data"])

    def _visible_property(self, portal, slug, queryset=None):
        qs = queryset if queryset is not None else visible_properties(portal)
        prop = qs.filter(Q(slug=slug) | Q(reference_code__iexact=slug)).first()
        if prop is None:
            raise NotFound("Imóvel não encontrado.")
        return prop

    def _detail_payload(self, portal, slug, com_relacionados=True):
        """
        Monta o detalhe do imóvel e os dados mínimos para registrar a visualização

        Args:
            portal: portal da requisição
            slug: slug ou código do imóvel
            com_relacionados: calcula os imóveis relacionados (o site busca à parte)

        Returns:
            ``{"data": {property, related, related_links}, "track": {property_id, reference_code, advertiser_id}}``
        """
        qs = with_card_data(visible_properties(portal), all_photos=True).select_related("advertiser", "advertiser__portal").prefetch_related("fees")
        prop = self._visible_property(portal, slug, qs)
        attach_advertiser_totals(portal, [prop.advertiser])
        related = SearchService(portal).related(prop) if com_relacionados else []
        ctx = {"request": self.request}
        return {
            "data": {
                "property": PublicPropertyDetailSerializer(prop, context=ctx).data,
                "related": PublicPropertyCardSerializer(related, many=True, context=ctx).data,
                "related_links": self._related_links(prop),
            },
            "track": {"property_id": prop.pk, "reference_code": prop.reference_code, "advertiser_id": prop.advertiser_id},
        }

    @action(detail=True, methods=["get"], url_path="related")
    def related(self, request, portal_slug=None, slug=None):
        """
        Imóveis relacionados ao informado (mesmo tipo e cidade, preço mais próximo)

        Returns:
            envelope com até 6 cards; 404 se o imóvel não estiver visível no portal
        """
        portal = self.get_portal()

        def montar():
            prop = self._visible_property(portal, slug)
            itens = SearchService(portal).related(prop)
            return PublicPropertyCardSerializer(itens, many=True, context={"request": request}).data

        dados = cached("listing", montar, portal=portal.slug, item=(slug or "").lower(), params={"view": "related"})
        return envelope_success(data=dados)

    @action(detail=False, methods=["get"], url_path="by-ids")
    def by_ids(self, request, portal_slug=None):
        """
        Cards dos imóveis informados em `?ids=a,b,c` (favoritos do visitante)

        Returns:
            envelope com cards, só dos imóveis visíveis no portal
        """
        portal = self.get_portal()
        ids = [i.strip() for i in (request.query_params.get("ids") or "").split(",") if i.strip()][:MAX_IDS]
        if not ids:
            return envelope_success(data=[])

        def montar():
            por_id = {str(p.pk): p for p in with_card_data(visible_properties(portal).filter(pk__in=ids))}
            ordenados = [por_id[i] for i in ids if i in por_id]
            return PublicPropertyCardSerializer(ordenados, many=True, context={"request": request}).data

        return envelope_success(data=cached("listing", montar, portal=portal.slug, params={"view": "by-ids", "ids": ids}))

    @action(detail=False, methods=["post"], url_path="inquiries")
    def inquiries(self, request, portal_slug=None):
        """
        Mensagem do visitante ao anunciante de um imóvel ("Fale com o anunciante")

        Returns:
            envelope com `{id}`; 403 se o remetente estiver bloqueado
        """
        portal = self.get_portal()
        serializer = PublicInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        prop = visible_properties(portal).select_related("advertiser").filter(pk=dados["property"]).first()
        if prop is None:
            raise ValidationError({"property": ["Imóvel não encontrado."]})
        ip = client_ip(request)
        ensure_sender_allowed(dados["email"], ip)
        inquiry = PropertyInquiry.objects.create(
            advertiser=prop.advertiser,
            property=prop,
            property_reference_code=prop.reference_code,
            portal=portal,
            name=dados["name"],
            email=dados["email"],
            phone=dados.get("phone", ""),
            message=dados["message"],
            contact_preferences=dados.get("contact_preferences", []),
            ip_address=ip,
            referer=(request.META.get("HTTP_REFERER") or "")[:2000],
            is_mobile=is_mobile(request),
        )
        return envelope_success(data={"id": inquiry.pk}, http_status=201)

    @action(detail=False, methods=["post"], url_path="contact-clicks")
    def contact_clicks(self, request, portal_slug=None):
        """
        Registra clique em "ver telefone" ou WhatsApp (estatística do anunciante)

        Returns:
            envelope com `{ok: true}`
        """
        portal = self.get_portal()
        serializer = PublicContactClickSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        prop = Property.objects.filter(pk=dados["property"]).select_related("advertiser").first() if dados.get("property") else None
        advertiser = prop.advertiser if prop else Advertiser.objects.filter(pk=dados.get("advertiser")).first()
        if advertiser is None:
            raise ValidationError({"advertiser": ["Anunciante não encontrado."]})
        PropertyContactClick.objects.create(
            property=prop,
            property_reference_code=prop.reference_code if prop else "",
            advertiser=advertiser,
            portal=portal,
            channel=dados["channel"],
            ip_address=client_ip(request),
            is_mobile=is_mobile(request),
        )
        return envelope_success(data={"ok": True})

    @staticmethod
    def _related_links(prop):
        """Combinações objetivo + tipo + bairro/cidade para links de SEO no detalhe."""
        links = []
        bairro = prop.neighborhood
        for purpose in PURPOSE_PRICE_FIELD:
            if bairro:
                links.append({"purpose": purpose, "property_type": {"name": prop.property_type.name, "slug": prop.property_type.slug}, "city": {"name": prop.city.name, "slug": prop.city.slug, "state_code": prop.city.state.code}, "neighborhood": {"name": bairro.name, "slug": bairro.slug}})
            links.append({"purpose": purpose, "property_type": {"name": prop.property_type.name, "slug": prop.property_type.slug}, "city": {"name": prop.city.name, "slug": prop.city.slug, "state_code": prop.city.state.code}, "neighborhood": None})
        return links
