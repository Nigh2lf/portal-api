from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Advertiser, BlockedSender, Portal, Property, PropertyContactClick, PropertyInquiry, PropertyView
from public.modules.portal.serializer import PublicPropertyCardSerializer
from public.modules.property.serializer import (
    PublicContactClickSerializer,
    PublicInquirySerializer,
    PublicPropertyDetailSerializer,
    PublicSearchResultSerializer,
)
from public.modules.property.service import PURPOSE_PRICE_FIELD, SearchFilters, SearchService
from public.services.scope import property_visibility_q, visible_properties, with_card_data

MAX_IDS = 100


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


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
        portal = Portal.objects.filter(slug=self.kwargs.get("portal_slug"), is_active=True).first()
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
        resultado = service.search(filters)
        if request.query_params.get("track", "1") != "0":
            service.log(filters, resultado["applied"], request)
        return envelope_success(data=PublicSearchResultSerializer(resultado, context={"request": request}).data)

    def retrieve(self, request, portal_slug=None, slug=None):
        """
        Detalhe do imóvel (por slug ou código) com anunciante, relacionados e links

        Returns:
            envelope com `{property, related, related_links}`; 404 se não visível no portal
        """
        portal = self.get_portal()
        qs = with_card_data(visible_properties(portal)).select_related("advertiser", "advertiser__portal").prefetch_related("fees")
        prop = qs.filter(Q(slug=slug) | Q(reference_code__iexact=slug)).first()
        if prop is None:
            raise NotFound("Imóvel não encontrado.")
        self._annotate_advertiser_totals(prop.advertiser, portal)
        if request.query_params.get("track", "1") != "0":
            PropertyView.objects.create(
                property=prop,
                property_reference_code=prop.reference_code,
                advertiser=prop.advertiser,
                portal=portal,
                ip_address=client_ip(request),
                referer=(request.META.get("HTTP_REFERER") or "")[:2000],
                is_mobile=is_mobile(request),
            )
        service = SearchService(portal)
        related = service.related(prop)
        return envelope_success(
            data={
                "property": PublicPropertyDetailSerializer(prop, context={"request": request}).data,
                "related": PublicPropertyCardSerializer(related, many=True, context={"request": request}).data,
                "related_links": self._related_links(prop),
            }
        )

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
        qs = with_card_data(visible_properties(portal).filter(pk__in=ids))
        por_id = {str(p.pk): p for p in qs}
        ordenados = [por_id[i] for i in ids if i in por_id]
        return envelope_success(data=PublicPropertyCardSerializer(ordenados, many=True, context={"request": request}).data)

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
        bloqueado = BlockedSender.objects.filter(is_active=True).filter(Q(email__iexact=dados["email"]) | Q(ip_address=ip)).exists()
        if bloqueado:
            raise PermissionDenied("Remetente bloqueado.")
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
    def _annotate_advertiser_totals(advertiser, portal):
        vis = property_visibility_q(portal)
        totais = Advertiser.objects.filter(pk=advertiser.pk).aggregate(
            total_properties=Count("properties", filter=vis, distinct=True),
            total_sale=Count("properties", filter=vis & Q(properties__sale_price__isnull=False), distinct=True),
            total_rent=Count("properties", filter=vis & Q(properties__rent_price__isnull=False), distinct=True),
            total_seasonal=Count("properties", filter=vis & Q(properties__seasonal_rent_price__isnull=False), distinct=True),
        )
        for chave, valor in totais.items():
            setattr(advertiser, chave, valor)

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
