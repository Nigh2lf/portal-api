"""Escopo de visibilidade do site público: o que cada portal mostra."""

from django.db.models import Count, Prefetch, Q

from core.models import Advertiser, Portal, Property, PropertyPhoto


def portal_ids(portal: Portal):
    return [portal.pk, *portal.combined_portals.values_list("pk", flat=True)]


def city_ids(portal: Portal):
    return list(portal.portal_cities.values_list("city_id", flat=True))


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


def with_card_data(queryset):
    """Preload para o card de imóvel: zero query por linha no serializer."""
    return (
        queryset.select_related("property_type", "city", "city__state", "neighborhood", "advertiser")
        .prefetch_related(
            Prefetch("photos", queryset=PropertyPhoto.objects.order_by("sort_order", "created_at")),
            "features",
        )
        .annotate(photos_count=Count("photos", distinct=True))
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
