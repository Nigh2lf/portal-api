"""Nome de tipo, cidade e bairro vindo do feed → registro do catálogo.

Compara sem acento e sem diferenciar maiúsculas, pelo nome e pelos ``import_aliases``
(a coluna ``Regras`` do legado). Tipo desconhecido vira "Outros"; bairro desconhecido
fica como texto livre (``neighborhood_name``); cidade desconhecida rejeita o imóvel.
"""

from __future__ import annotations

from core.models import AdvertiserCity, City, Neighborhood, PortalCity, PropertyType
from xml_import.formats.base import normalize_name

OTHERS_TYPE_LEGACY_ID = 20


def _keys(name, aliases):
    yield normalize_name(name)
    for alias in aliases or []:
        key = normalize_name(alias)
        if key:
            yield key


class Resolver:
    def __init__(self, advertiser):
        self.types = {}
        for t in PropertyType.objects.all().order_by("-is_active", "sort_order"):
            for k in _keys(t.name, t.import_aliases):
                self.types.setdefault(k, t)
        self.other_type = (
            PropertyType.objects.filter(legacy_id=OTHERS_TYPE_LEGACY_ID).first()
            or PropertyType.objects.filter(slug__startswith="outro").first()
        )
        self.cities = {}
        for c in City.objects.select_related("state"):
            for k in _keys(c.name, c.import_aliases):
                self.cities.setdefault(k, []).append(c)
        # Nomes repetidos entre estados: vale a cidade em que o anunciante atua, depois as do portal.
        self.preferred = set(
            AdvertiserCity.objects.filter(advertiser=advertiser).values_list("city_id", flat=True)
        )
        self.preferred |= set(
            PortalCity.objects.filter(portal_id=advertiser.portal_id).values_list(
                "city_id", flat=True
            )
        )
        self.neighborhoods = {}

    def property_type(self, name):
        return self.types.get(normalize_name(name)) or self.other_type

    def city(self, name, state_code=""):
        candidates = self.cities.get(normalize_name(name)) or []
        if len(candidates) <= 1:
            return candidates[0] if candidates else None
        state_code = (state_code or "").strip().upper()
        return (
            next((c for c in candidates if c.pk in self.preferred), None)
            or next(
                (c for c in candidates if state_code and c.state.code.upper() == state_code), None
            )
            or candidates[0]
        )

    def neighborhood(self, city, name):
        if city is None or not (name or "").strip():
            return None
        if city.pk not in self.neighborhoods:
            mapping = {}
            for n in Neighborhood.objects.filter(city=city):
                for k in _keys(n.name, n.import_aliases):
                    mapping.setdefault(k, n)
            self.neighborhoods[city.pk] = mapping
        return self.neighborhoods[city.pk].get(normalize_name(name))
