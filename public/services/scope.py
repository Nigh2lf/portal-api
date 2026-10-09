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


def with_card_data(queryset):
    """Preload para o card de imóvel: zero query por linha no serializer."""
    return (
        queryset.select_related("property_type", "city", "city__state", "neighborhood", "advertiser")
        .prefetch_related(
            Prefetch("photos", queryset=PropertyPhoto.objects.order_by("sort_order", "created_at")),
            "features",
        )
        .annotate(photos_count=photos_count_subquery())
    )


def property_visibility_q(portal: Portal, prefix="properties"):
    """Mesmas regras de `visible_properties` como Q para usar em annotate(Count(...))."""
    return Q(
        **{
            f"{prefix}__status": Property.Status.PUBLISHED,
            f"{prefix}__is_active": True,
            f"{prefix}__deleted_at__isnull": True,
            f"{prefix}__city_id__in": city_ids(portal),
        }
    )
