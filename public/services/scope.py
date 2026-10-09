"""Escopo de visibilidade do site público: o que cada portal mostra."""

from django.db.models import Count, Exists, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce

from core.models import Advertiser, Portal, PortalCity, Property, PropertyPhoto
from core.services.public_cache import cached


def portal_queryset():
    return (
        Portal.objects.filter(is_active=True)
        .select_related("main_city", "main_city__state")
        .prefetch_related(
            Prefetch("portal_cities", queryset=PortalCity.objects.select_related("city", "city__state").order_by("sort_order")),
            "combined_portals",
            "menu_items",
        )
    )


def cached_portal(slug):
    """Portal ativo pelo slug (com cidades e menus pré-carregados), em cache; ``None`` se não existir."""
    return cached("portal", lambda: portal_queryset().filter(slug=slug).first(), portal=slug, params={"view": "object"})


def portal_ids(portal: Portal):
    """Ids do portal e dos combinados; sem query quando o portal veio de `portal_queryset`."""
    return [portal.pk, *(p.pk for p in portal.combined_portals.all())]


def city_ids(portal: Portal):
    """Ids das cidades cobertas; sem query quando o portal veio de `portal_queryset`."""
    return [pc.city_id for pc in portal.portal_cities.all()]


def visible_properties(portal: Portal):
    """Imóveis publicados, ativos, de anunciantes ativos no portal (ou combinados) e nas cidades cobertas."""
    return Property.objects.filter(
        status=Property.Status.PUBLISHED,
        is_active=True,
        deleted_at__isnull=True,
        advertiser__is_published=True,
        advertiser__deleted_at__isnull=True,
        advertiser__portal_id__in=portal_ids(portal),
        city_id__in=city_ids(portal),
    )


def visible_advertisers(portal: Portal):
    return Advertiser.objects.filter(is_published=True, deleted_at__isnull=True, portal_id__in=portal_ids(portal))


def photos_count_subquery():
    """Total de fotos do imóvel como subconsulta correlacionada.

    Não usar ``Count("photos")`` em listagens: o LEFT JOIN multiplica cada imóvel
    pelas fotos (~17) e o GROUP BY obriga o MySQL a gravar todas as colunas do
    imóvel e do anunciante numa tabela temporária antes do LIMIT (6 s na busca
    de Petrópolis). A subconsulta é um lookup por índice por linha.
    """
    contagem = PropertyPhoto.objects.filter(property=OuterRef("pk")).order_by().values("property").annotate(c=Count("id")).values("c")
    return Coalesce(Subquery(contagem, output_field=IntegerField()), 0)


def has_photo_exists():
    """``True`` se o imóvel tem ao menos uma foto (para ordenar quem tem foto primeiro)."""
    return Exists(PropertyPhoto.objects.filter(property=OuterRef("pk")))


def with_card_data(queryset, all_photos=False):
    """
    Preload para o card de imóvel: zero query por linha no serializer

    Args:
        queryset: imóveis a carregar
        all_photos: ``True`` traz a galeria inteira (detalhe); o card só usa a capa

    Returns:
        queryset com joins, fotos, características e ``photos_count``
    """
    photos = PropertyPhoto.objects.order_by("sort_order", "created_at")
    if not all_photos:
        # ~17 fotos por imóvel, espalhadas pela tabela (PK UUID): carregar todas para mostrar
        # uma era a maior leitura de disco da busca.
        photos = photos.filter(is_cover=True)
    return (
        queryset.select_related("property_type", "city", "city__state", "neighborhood", "advertiser")
        .prefetch_related(Prefetch("photos", queryset=photos), "features")
        .annotate(photos_count=photos_count_subquery())
    )


ADVERTISER_TOTAL_FIELDS = ("total_properties", "total_sale", "total_rent", "total_seasonal")


def attach_advertiser_totals(portal: Portal, advertisers):
    """
    Preenche nos anunciantes os totais de imóveis visíveis no portal, por objetivo

    Uma consulta agrupada em ``Property`` para todos; ``Count("properties", distinct=True)``
    no queryset de anunciantes multiplica as linhas largas do anunciante pelos imóveis.

    Args:
        portal: portal da requisição
        advertisers: anunciantes já visíveis no portal

    Returns:
        lista dos mesmos anunciantes com ``total_properties``, ``total_sale``, ``total_rent`` e ``total_seasonal``
    """
    advertisers = list(advertisers)
    if not advertisers:
        return advertisers
    rows = (
        visible_properties(portal)
        .filter(advertiser_id__in=[a.pk for a in advertisers])
        .order_by()
        .values("advertiser_id")
        .annotate(
            total_properties=Count("id"),
            total_sale=Count("id", filter=Q(sale_price__isnull=False)),
            total_rent=Count("id", filter=Q(rent_price__isnull=False)),
            total_seasonal=Count("id", filter=Q(seasonal_rent_price__isnull=False)),
        )
    )
    totals = {row["advertiser_id"]: row for row in rows}
    for advertiser in advertisers:
        row = totals.get(advertiser.pk, {})
        for name in ADVERTISER_TOTAL_FIELDS:
            setattr(advertiser, name, row.get(name, 0))
    return advertisers
