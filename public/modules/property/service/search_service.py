from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Case, Count, F, IntegerField, Max, Q, Value, When
from rest_framework.exceptions import ValidationError

from core.models import City, Neighborhood, Portal, Property, PropertyType, SearchLog
from core.services.deferred_writes import defer
from public.services.scope import city_ids, has_photo_exists, visible_properties, with_card_data

PURPOSE_PRICE_FIELD = {"SALE": "sale_price", "RENT": "rent_price", "SEASONAL": "seasonal_rent_price"}
ORDERINGS = {"recent": "-updated_at", "price_asc": "price_value", "price_desc": "-price_value"}
MAX_PAGE_SIZE = 60
MAX_NEIGHBORHOODS = 20


@dataclass
class SearchFilters:
    purpose: str = "SALE"
    property_type: str | None = None
    city: str | None = None
    neighborhoods: list[str] = field(default_factory=list)
    condominium: str | None = None
    bedrooms: list[int] = field(default_factory=list)
    parking: int | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    code: str | None = None
    advertiser: str | None = None
    ordering: str = "recent"
    page: int = 1
    page_size: int = 30

    @classmethod
    def from_query(cls, params, default_page_size=30):
        def inteiro(nome, minimo=None):
            raw = params.get(nome)
            if raw in (None, ""):
                return None
            try:
                valor = int(raw)
            except ValueError as exc:
                raise ValidationError({nome: ["Informe um número inteiro."]}) from exc
            if minimo is not None and valor < minimo:
                raise ValidationError({nome: [f"Mínimo {minimo}."]})
            return valor

        def decimal(nome):
            raw = params.get(nome)
            if raw in (None, ""):
                return None
            try:
                return Decimal(str(raw).replace(",", "."))
            except Exception as exc:  # noqa: BLE001 - Decimal lança InvalidOperation
                raise ValidationError({nome: ["Informe um valor numérico."]}) from exc

        purpose = (params.get("purpose") or "SALE").upper()
        if purpose not in PURPOSE_PRICE_FIELD:
            raise ValidationError({"purpose": ["Use SALE, RENT ou SEASONAL."]})
        condominium = params.get("condominium") or None
        if condominium and condominium not in ("inside", "outside"):
            raise ValidationError({"condominium": ["Use inside ou outside."]})
        ordering = params.get("ordering") or "recent"
        if ordering not in ORDERINGS:
            raise ValidationError({"ordering": ["Use recent, price_asc ou price_desc."]})
        bedrooms = []
        for parte in str(params.get("bedrooms") or "").split(","):
            parte = parte.strip()
            if parte.isdigit() and 1 <= int(parte) <= 4:
                bedrooms.append(int(parte))
        page_size = inteiro("page_size", 1) or default_page_size
        bairros = []
        for parte in str(params.get("neighborhood") or "").split(","):
            parte = parte.strip()
            if parte and parte not in bairros:
                bairros.append(parte)
        if len(bairros) > MAX_NEIGHBORHOODS:
            raise ValidationError({"neighborhood": [f"Escolha no máximo {MAX_NEIGHBORHOODS} bairros."]})
        return cls(
            purpose=purpose,
            property_type=params.get("property_type") or None,
            city=params.get("city") or None,
            neighborhoods=bairros,
            condominium=condominium,
            bedrooms=sorted(set(bedrooms)),
            parking=inteiro("parking", 1),
            price_min=decimal("price_min"),
            price_max=decimal("price_max"),
            code=(params.get("code") or "").strip() or None,
            advertiser=params.get("advertiser") or None,
            ordering=ordering,
            page=inteiro("page", 1) or 1,
            page_size=min(page_size, MAX_PAGE_SIZE),
        )


class SearchService:
    def __init__(self, portal: Portal):
        self.portal = portal

    def resolve(self, filters: SearchFilters):
        """Resolve os slugs dos filtros em registros (ou None / lista vazia quando não existem)."""
        city = City.objects.filter(slug=filters.city).select_related("state").first() if filters.city else None
        neighborhoods = []
        if filters.neighborhoods:
            qs = Neighborhood.objects.filter(slug__in=filters.neighborhoods).select_related("city", "city__state")
            if city:
                qs = qs.filter(city=city)
            else:
                # Sem cidade, "centro" existe em várias: prefere a cidade principal, depois as do portal.
                qs = qs.filter(city__in=city_ids(self.portal)).order_by(
                    Case(When(city_id=self.portal.main_city_id, then=Value(0)), default=Value(1), output_field=IntegerField())
                )
            por_slug = {}
            for n in qs:
                por_slug.setdefault(n.slug, n)
            neighborhoods = [por_slug[s] for s in filters.neighborhoods if s in por_slug]
            cidades = {n.city_id for n in neighborhoods}
            if city is None and len(cidades) == 1:
                city = neighborhoods[0].city
        property_type = PropertyType.objects.filter(slug=filters.property_type).first() if filters.property_type else None
        return {
            "city": city,
            "neighborhoods": neighborhoods,
            "neighborhood": neighborhoods[0] if len(neighborhoods) == 1 else None,
            "property_type": property_type,
        }

    def base_queryset(self, filters: SearchFilters, resolved):
        """Filtros que não dependem do objetivo (usados também nos contadores das abas)."""
        qs = visible_properties(self.portal)
        if filters.property_type:
            qs = qs.filter(property_type=resolved["property_type"]) if resolved["property_type"] else qs.none()
        if filters.city:
            qs = qs.filter(city=resolved["city"]) if resolved["city"] else qs.none()
        if filters.neighborhoods:
            qs = qs.filter(neighborhood__in=resolved["neighborhoods"]) if resolved["neighborhoods"] else qs.none()
        if filters.advertiser:
            qs = qs.filter(advertiser__slug=filters.advertiser)
        if filters.condominium == "inside":
            qs = qs.filter(is_in_condominium=True)
        elif filters.condominium == "outside":
            qs = qs.filter(is_in_condominium=False)
        if filters.bedrooms:
            cond = Q()
            for n in filters.bedrooms:
                cond |= Q(bedrooms__gte=4) if n >= 4 else Q(bedrooms=n)
            qs = qs.filter(cond)
        if filters.parking:
            qs = qs.filter(parking_spaces__gte=6) if filters.parking >= 6 else qs.filter(parking_spaces=filters.parking)
        if filters.code:
            qs = qs.filter(reference_code__icontains=filters.code)
        return qs

    def search(self, filters: SearchFilters):
        resolved = self.resolve(filters)
        base = self.base_queryset(filters, resolved)
        counters = base.aggregate(
            sale=Count("id", filter=Q(sale_price__isnull=False)),
            rent=Count("id", filter=Q(rent_price__isnull=False)),
            seasonal=Count("id", filter=Q(seasonal_rent_price__isnull=False)),
        )
        price_field = PURPOSE_PRICE_FIELD[filters.purpose]
        qs = base.filter(**{f"{price_field}__isnull": False})
        max_price = qs.aggregate(m=Max(price_field))["m"] or Decimal(0)
        if filters.price_min is not None:
            qs = qs.filter(**{f"{price_field}__gte": filters.price_min})
        if filters.price_max is not None:
            qs = qs.filter(**{f"{price_field}__lte": filters.price_max})

        total = qs.count()
        total_pages = max(1, -(-total // filters.page_size))
        page = min(max(1, filters.page), total_pages)
        inicio = (page - 1) * filters.page_size

        # Duas etapas: (1) só os ids da página, ordenados — a tabela temporária que o
        # MySQL monta para ordenar por colunas calculadas fica estreita; (2) as linhas
        # completas (joins + fotos) só dos 30 imóveis. `has_photo` por EXISTS, nunca
        # por JOIN com fotos (ver `photos_count_subquery`).
        order = ORDERINGS[filters.ordering]
        ordenado = qs.annotate(price_value=F(price_field), has_photo=has_photo_exists(), ad_rank=Property.ad_rank_expression()).order_by(
            "-ad_rank", "-has_photo", order, "-updated_at"
        )
        ids = list(ordenado.values_list("pk", flat=True)[inicio : inicio + filters.page_size])
        por_id = {p.pk: p for p in with_card_data(Property.objects.filter(pk__in=ids)).annotate(price_value=F(price_field))}
        results = [por_id[i] for i in ids if i in por_id]
        return {
            "results": results,
            "count": total,
            "page": page,
            "page_size": filters.page_size,
            "total_pages": total_pages,
            "counters": counters,
            "max_price": max_price,
            "applied": resolved,
        }

    def log(self, filters: SearchFilters, resolved, request):
        """Alimenta "mais procurados"; só na primeira página, para não inflar com paginação."""
        if filters.page != 1:
            return
        defer(
            SearchLog.objects.create,
            portal=self.portal,
            purpose=filters.purpose,
            property_type=resolved["property_type"],
            city=resolved["city"],
            neighborhood=resolved["neighborhood"],
            bedrooms=filters.bedrooms,
            is_in_condominium=None if not filters.condominium else filters.condominium == "inside",
            min_price=filters.price_min,
            max_price=filters.price_max,
            page=filters.page,
            is_mobile="Mobile" in (request.META.get("HTTP_USER_AGENT") or ""),
        )

    def related(self, prop: Property, limit=6):
        """Mesmo tipo e cidade, preço mais próximo no mesmo objetivo."""
        purpose = "SALE" if prop.sale_price is not None else "RENT" if prop.rent_price is not None else "SEASONAL"
        price_field = PURPOSE_PRICE_FIELD[purpose]
        preco = getattr(prop, price_field) or Decimal(0)
        qs = (
            visible_properties(self.portal)
            .exclude(pk=prop.pk)
            .filter(property_type=prop.property_type, city=prop.city, **{f"{price_field}__isnull": False})
        )
        candidatos = list(with_card_data(qs).annotate(price_value=F(price_field))[:200])
        candidatos.sort(key=lambda p: abs((p.price_value or Decimal(0)) - preco))
        return candidatos[:limit]
