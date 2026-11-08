"""Filtros e totais da listagem de lotes da importação XML (``GET /xml-import-runs/batches/``)."""

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters

from core.models import XmlImportBatch, XmlImportRun

PROPERTY_TOTALS = ("total_properties", "valid_properties", "invalid_properties")
BATCH_ORDERING = ("created_at", "started_at", "finished_at", "total_advertisers", "failed")


class XmlImportBatchFilter(filters.FilterSet):
    """``advertiser`` e ``search`` acham os lotes em que o anunciante rodou (pelo id ou pelo nome)."""

    advertiser = filters.UUIDFilter(method="filter_advertiser")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = XmlImportBatch
        fields = {
            "status": ["exact"],
            "origin": ["exact"],
            "scope": ["exact"],
            "created_at": ["gte", "lte"],
        }

    def filter_advertiser(self, queryset, name, value):
        runs = XmlImportRun.objects.filter(advertiser=value, batch__isnull=False)
        return queryset.filter(pk__in=runs.values("batch_id"))

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        runs = XmlImportRun.objects.filter(advertiser__name__icontains=value, batch__isnull=False)
        return queryset.filter(pk__in=runs.values("batch_id"))


def with_property_totals(queryset):
    """Anota em cada lote a soma dos imóveis das suas execuções (no XML, válidos e inválidos)."""
    return queryset.annotate(
        **{field: Coalesce(Sum(f"runs__{field}"), 0) for field in PROPERTY_TOTALS}
    )


def property_totals(batch) -> dict:
    """Totais de imóveis do lote: lê a anotação de ``with_property_totals`` ou soma na hora."""
    if all(hasattr(batch, field) for field in PROPERTY_TOTALS):
        return {field: getattr(batch, field) or 0 for field in PROPERTY_TOTALS}
    sums = batch.runs.aggregate(**{f"sum_{field}": Sum(field) for field in PROPERTY_TOTALS})
    return {field: sums[f"sum_{field}"] or 0 for field in PROPERTY_TOTALS}


def batch_ordering(value) -> tuple[str, ...]:
    """Ordenação pedida em ``?ordering=`` (só campos de ``BATCH_ORDERING``); padrão: mais recente primeiro."""
    field = (value or "").strip()
    if field.lstrip("-") in BATCH_ORDERING:
        return (field, "-created_at")
    return ("-created_at",)
