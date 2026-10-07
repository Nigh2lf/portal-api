"""Nome de tipo, cidade e bairro vindo do feed → registro do catálogo.

Compara sem acento e sem diferenciar maiúsculas, pelo nome e pelos ``import_aliases``
(a coluna ``Regras`` do legado). Tipo desconhecido vira "Outros"; bairro desconhecido
fica como texto livre (``neighborhood_name``); cidade desconhecida rejeita o imóvel.
"""

from __future__ import annotations

from core.models import AdvertiserCity, City, Neighborhood, PortalCity, PropertyType
from importacao.formatos.base import normalizar_nome

TIPO_OUTROS_LEGACY_ID = 20


def _chaves(nome, aliases):
    yield normalizar_nome(nome)
    for alias in aliases or []:
        chave = normalizar_nome(alias)
        if chave:
            yield chave


class Resolvedor:
    def __init__(self, advertiser):
        self.tipos = {}
        for t in PropertyType.objects.all().order_by("-is_active", "sort_order"):
            for k in _chaves(t.name, t.import_aliases):
                self.tipos.setdefault(k, t)
        self.tipo_outros = (
            PropertyType.objects.filter(legacy_id=TIPO_OUTROS_LEGACY_ID).first()
            or PropertyType.objects.filter(slug__startswith="outro").first()
        )
        self.cidades = {}
        for c in City.objects.select_related("state"):
            for k in _chaves(c.name, c.import_aliases):
                self.cidades.setdefault(k, []).append(c)
        # Nomes repetidos entre estados: vale a cidade em que o anunciante atua, depois as do portal.
        self.preferidas = set(AdvertiserCity.objects.filter(advertiser=advertiser).values_list("city_id", flat=True))
        self.preferidas |= set(PortalCity.objects.filter(portal_id=advertiser.portal_id).values_list("city_id", flat=True))
        self.bairros = {}

    def tipo(self, nome):
        return self.tipos.get(normalizar_nome(nome)) or self.tipo_outros

    def cidade(self, nome, uf=""):
        candidatas = self.cidades.get(normalizar_nome(nome)) or []
        if len(candidatas) <= 1:
            return candidatas[0] if candidatas else None
        uf = (uf or "").strip().upper()
        return (
            next((c for c in candidatas if c.pk in self.preferidas), None)
            or next((c for c in candidatas if uf and c.state.code.upper() == uf), None)
            or candidatas[0]
        )

    def bairro(self, cidade, nome):
        if cidade is None or not (nome or "").strip():
            return None
        if cidade.pk not in self.bairros:
            mapa = {}
            for b in Neighborhood.objects.filter(city=cidade):
                for k in _chaves(b.name, b.import_aliases):
                    mapa.setdefault(k, b)
            self.bairros[cidade.pk] = mapa
        return self.bairros[cidade.pk].get(normalizar_nome(nome))
