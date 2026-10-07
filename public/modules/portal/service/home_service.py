from datetime import timedelta

from django.db.models import Case, CharField, Count, Prefetch, Q, Value, When
from django.utils import timezone

from core.models import (
    Ad,
    Banner,
    City,
    Feature,
    Neighborhood,
    Portal,
    Property,
    PropertyPhoto,
    PropertyType,
    SearchLog,
)
from public.services.scope import photos_count_subquery

PURPOSE_CASE = Case(
    When(sale_price__isnull=False, then=Value("SALE")),
    When(rent_price__isnull=False, then=Value("RENT")),
    default=Value("SEASONAL"),
    output_field=CharField(),
)


class HomeService:
    def __init__(self, portal: Portal):
        self.portal = portal

    def scope(self):
        """Imóveis visíveis no portal: publicados, de anunciantes ativos no portal (ou combinados) e nas cidades cobertas."""
        portais = [self.portal.pk, *self.portal.combined_portals.values_list("pk", flat=True)]
        cidades = self.portal.portal_cities.values_list("city_id", flat=True)
        return Property.objects.filter(
            status=Property.Status.PUBLISHED,
            is_active=True,
            deleted_at__isnull=True,
            advertiser__is_published=True,
            advertiser__deleted_at__isnull=True,
            advertiser__portal_id__in=portais,
            city_id__in=cidades,
        )

    def cards_queryset(self, queryset):
        return (
            queryset.select_related("property_type", "city", "city__state", "neighborhood", "advertiser")
            .prefetch_related(
                Prefetch("photos", queryset=PropertyPhoto.objects.order_by("sort_order", "created_at")),
                "features",
            )
            .annotate(photos_count=photos_count_subquery())
        )

    def featured(self, limit=12):
        """Destaques do portal; completa com os mais recentes quando há menos que o limite."""
        destaques = list(
            self.cards_queryset(self.scope().exclude(ad_type=Property.AdType.NORMAL))
            .annotate(ad_rank=Property.ad_rank_expression())
            .order_by("-ad_rank", "-updated_at")[:limit]
        )
        if len(destaques) < limit:
            ids = [p.pk for p in destaques]
            extra = self.cards_queryset(self.scope().exclude(pk__in=ids)).order_by("-updated_at")[: limit - len(destaques)]
            destaques.extend(extra)
        return destaques

    def total_properties(self):
        return self.scope().count()

    def top_searches(self, limit=15, days=90):
        """Combinações mais buscadas (SearchLog); sem registros, usa as combinações com mais anúncios."""
        desde = timezone.now() - timedelta(days=days)
        logs = (
            SearchLog.objects.filter(portal=self.portal, created_at__gte=desde, property_type__isnull=False, neighborhood__isnull=False)
            .values(
                "purpose",
                "property_type__name",
                "property_type__slug",
                "city__name",
                "city__slug",
                "city__state__code",
                "neighborhood__name",
                "neighborhood__slug",
            )
            .annotate(total=Count("id"))
            .order_by("-total")[:limit]
        )
        rows = list(logs)
        if not rows:
            rows = list(
                self.scope()
                .exclude(neighborhood=None)
                .annotate(purpose=PURPOSE_CASE)
                .values(
                    "purpose",
                    "property_type__name",
                    "property_type__slug",
                    "city__name",
                    "city__slug",
                    "city__state__code",
                    "neighborhood__name",
                    "neighborhood__slug",
                )
                .annotate(total=Count("id"))
                .order_by("-total")[:limit]
            )
        return [
            {
                "purpose": r["purpose"],
                "property_type": {"name": r["property_type__name"], "slug": r["property_type__slug"]},
                "city": {"name": r["city__name"], "slug": r["city__slug"], "state_code": r["city__state__code"]},
                "neighborhood": {"name": r["neighborhood__name"], "slug": r["neighborhood__slug"]},
                "total": r["total"],
            }
            for r in rows
        ]

    def top_neighborhoods(self, limit=15):
        rows = (
            self.scope()
            .exclude(neighborhood=None)
            .values("neighborhood_id", "neighborhood__name", "neighborhood__slug", "city__name", "city__slug", "city__state__code")
            .annotate(total=Count("id"))
            .order_by("-total", "neighborhood__name")[:limit]
        )
        return [
            {
                "neighborhood": {"id": r["neighborhood_id"], "name": r["neighborhood__name"], "slug": r["neighborhood__slug"]},
                "city": {"name": r["city__name"], "slug": r["city__slug"], "state_code": r["city__state__code"]},
                "total": r["total"],
            }
            for r in rows
        ]

    def banners(self):
        return Banner.objects.filter(is_active=True).filter(Q(portal=self.portal) | Q(portal__isnull=True)).order_by("-created_at")

    def ads(self, page=None, kind=None):
        agora = timezone.now()
        qs = Ad.objects.filter(portal=self.portal, is_active=True, starts_at__lte=agora, ends_at__gte=agora).select_related("placement")
        if page:
            qs = qs.filter(placement__page=page)
        if kind:
            qs = qs.filter(placement__kind=kind)
        return qs.order_by("-created_at")

    def catalog(self):
        """Opções do formulário de busca: tipos, cidades do portal e bairros com anúncios."""
        cidades_ids = list(self.portal.portal_cities.order_by("sort_order").values_list("city_id", flat=True))
        contagem = dict(
            self.scope().exclude(neighborhood=None).values_list("neighborhood_id").annotate(total=Count("id")).values_list("neighborhood_id", "total")
        )
        bairros = Neighborhood.objects.filter(pk__in=contagem.keys(), is_active=True).select_related("city").order_by("name")
        return {
            "property_types": PropertyType.objects.filter(is_active=True).order_by("sort_order", "name"),
            "cities": City.objects.filter(pk__in=cidades_ids, is_active=True).select_related("state").order_by("name"),
            "neighborhoods": [(b, contagem.get(b.pk, 0)) for b in bairros],
            "features": Feature.objects.filter(is_active=True).order_by("scope", "sort_order", "name"),
        }
