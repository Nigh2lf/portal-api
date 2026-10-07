"""Fluxo 3: compara os imóveis normalizados de um anunciante com o banco e aplica a diferença.

Regras (as do legado, com a inconsistência de destaque entre insert e update unificada):

- casa pelo código do anunciante (``reference_code``, sem diferenciar maiúsculas);
- só entram os N primeiros do feed, na ordem, até o limite de imóveis do plano;
- fotos limitadas ao plano; uma capa por imóvel (a marcada no feed, senão a primeira);
- destaque (1) e superdestaque (2) entram na ordem do feed até os limites do anunciante;
- imóvel do banco que não está no feed (ou ficou acima do limite) é excluído;
- feed sem imóveis não exclui nada;
- código barrado pela moderação, cidade desconhecida ou sem preço: ignorado e registrado;
- código repetido no banco para o mesmo anunciante: fica um, os demais são excluídos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify

from core.models import Feature, Property, PropertyFee, PropertyPhoto, RejectedProperty
from core.modules.property.service.property_service import PropertyService
from core.services.slug import unique_slug
from importacao.formatos.base import normalizar_nome
from importacao.services.resolvedor import Resolvedor

CAMPOS = (
    "reference_code", "status", "is_active", "ad_type", "property_type", "city", "neighborhood", "neighborhood_name",
    "is_in_condominium", "bedrooms", "suites", "bathrooms", "parking_spaces", "built_area", "total_area",
    "description", "sale_price", "rent_price", "seasonal_rent_price", "title", "deleted_at",
)
# Campos comparados para decidir se o imóvel mudou (o título deriva deles).
COMPARADOS = tuple(c for c in CAMPOS if c not in ("status", "title"))


@dataclass
class Resultado:
    total_feed: int = 0
    novos: list = field(default_factory=list)
    alterados: list = field(default_factory=list)
    iguais: int = 0
    excluidos: list = field(default_factory=list)
    ignorados: list = field(default_factory=list)

    def resumo(self):
        return {
            "total_feed": self.total_feed,
            "novos": len(self.novos),
            "alterados": len(self.alterados),
            "iguais": self.iguais,
            "excluidos": len(self.excluidos),
            "ignorados": len(self.ignorados),
        }

    def detalhes(self, limite=500):
        return {
            **self.resumo(),
            "codigos_novos": self.novos[:limite],
            "codigos_alterados": self.alterados[:limite],
            "codigos_excluidos": self.excluidos[:limite],
            "ignorados_lista": self.ignorados[:limite],
        }


def _dec(v):
    return Decimal(v) if v not in (None, "") else None


class Caracteristicas:
    """Características por nome (criadas na hora quando o feed traz uma nova)."""

    def __init__(self):
        self.cache = {}
        for f in Feature.objects.order_by("created_at"):
            self.cache.setdefault((f.scope, normalizar_nome(f.name)), f)

    def obter(self, scope, nome):
        # Sem acento e sem maiúsculas: "Quadra de tênis" do feed casa com "Quadra de tenis" do catálogo.
        chave = (scope, normalizar_nome(nome))
        if chave not in self.cache:
            self.cache[chave] = Feature.objects.create(
                scope=scope,
                name=nome.strip()[:100],
                slug=unique_slug(Feature, nome, max_length=100, scope={"scope": scope}),
                sort_order=99,
            )
        return self.cache[chave]


class Aplicador:
    def __init__(self, advertiser):
        self.advertiser = advertiser
        self.resolvedor = Resolvedor(advertiser)
        self.caracteristicas = Caracteristicas()
        self.limite_imoveis = advertiser.effective_property_limit or 0
        self.limite_fotos = advertiser.effective_photo_limit or 0
        self.limite_destaques = advertiser.effective_featured_limit or 0
        self.limite_super = advertiser.super_featured_limit or 0

    # ------------------------------------------------------------ montagem
    def _ad_type(self, destaque, contagem):
        if destaque == 2 and contagem["super"] < self.limite_super:
            contagem["super"] += 1
            return Property.AdType.SUPER_FEATURED
        if destaque >= 1 and contagem["destaque"] < self.limite_destaques:
            contagem["destaque"] += 1
            return Property.AdType.FEATURED
        return Property.AdType.NORMAL

    def _fotos(self, item):
        fotos = item["fotos"][: self.limite_fotos] if self.limite_fotos else item["fotos"]
        vistas, saida = set(), []
        for f in fotos:
            if f["url"] not in vistas:
                vistas.add(f["url"])
                saida.append({"url": f["url"], "capa": f["capa"]})
        if saida:
            capa = next((i for i, f in enumerate(saida) if f["capa"]), 0)
            for i, f in enumerate(saida):
                f["capa"] = i == capa
        return saida

    def _features(self, item):
        ids = []
        for scope, nomes in ((Feature.Scope.PROPERTY, item["infra_imovel"]), (Feature.Scope.CONDOMINIUM, item["infra_condominio"])):
            for nome in nomes:
                f = self.caracteristicas.obter(scope, nome)
                if f.pk not in ids:
                    ids.append(f.pk)
        return ids

    @staticmethod
    def _taxas(item):
        return [
            {
                "description": t["descricao"][:150],
                "amount": Decimal(t["valor"]),
                "period": PropertyFee.Period.YEARLY if "iptu" in t["descricao"].lower() else PropertyFee.Period.MONTHLY,
                "notes": (t.get("obs") or "")[:300],
            }
            for t in item["taxas"]
        ]

    def _valores(self, item, tipo, cidade, bairro, ad_type):
        valores = {
            "reference_code": item["codigo"][:45],
            "status": Property.Status.PUBLISHED,
            "is_active": True,
            "ad_type": ad_type,
            "property_type": tipo,
            "city": cidade,
            "neighborhood": bairro,
            "neighborhood_name": "" if bairro else item["bairro"][:120],
            "is_in_condominium": bool(item["dentro_condominio"]),
            "bedrooms": item["quartos"],
            "suites": item["suites"],
            "bathrooms": item["banheiros"],
            "parking_spaces": item["vagas"],
            "built_area": _dec(item["area_util"]),
            "total_area": _dec(item["area_total"]),
            "description": item["descricao"],
            "sale_price": _dec(item["preco_venda"]),
            "rent_price": _dec(item["preco_locacao"]),
            "seasonal_rent_price": _dec(item["preco_temporada"]),
            "deleted_at": None,
        }
        valores["title"] = PropertyService.build_title({**valores, "title": None, "slug": None})
        return valores

    # ------------------------------------------------------------- execução
    def executar(self, imoveis, simular=False):
        """
        Compara o feed normalizado com o banco e aplica (ou só calcula, em simulação)

        Args:
            imoveis: lista de imóveis normalizados
            simular: ``True`` não grava nada

        Returns:
            Resultado com o que entrou, mudou, saiu e foi ignorado
        """
        res = Resultado(total_feed=len(imoveis))
        if not imoveis:
            return res
        bloqueados = {c.lower() for c in RejectedProperty.objects.filter(advertiser=self.advertiser).values_list("property_reference_code", flat=True)}
        existentes, repetidos = {}, []
        # Ativos primeiro: com o mesmo código, fica o ativo mais antigo; os demais são excluídos.
        for p in Property.objects.filter(advertiser=self.advertiser).order_by(F("deleted_at").asc(nulls_first=True), "created_at"):
            chave = p.reference_code.strip().lower()
            if chave in existentes:
                repetidos.append(p)
            else:
                existentes[chave] = p

        contagem = {"destaque": 0, "super": 0}
        manter, vistos, aceitos = set(), set(), 0
        planos = []  # (prop, novo, valores, fotos, features, taxas)
        for item in imoveis:
            codigo = item["codigo"].strip()
            chave = codigo.lower()
            if not codigo:
                res.ignorados.append({"codigo": "", "motivo": "Imóvel sem código."})
                continue
            if chave in vistos:
                res.ignorados.append({"codigo": codigo, "motivo": "Código repetido no feed."})
                continue
            vistos.add(chave)
            if self.limite_imoveis and aceitos >= self.limite_imoveis:
                res.ignorados.append({"codigo": codigo, "motivo": f"Acima do limite do plano ({self.limite_imoveis} imóveis)."})
                continue
            if chave in bloqueados:
                res.ignorados.append({"codigo": codigo, "motivo": "Barrado pela moderação."})
                continue
            cidade = self.resolvedor.cidade(item["cidade"], item["uf"])
            if cidade is None:
                # Mantém o imóvel que já existe; a vaga do plano não é consumida.
                manter.add(chave)
                res.ignorados.append({"codigo": codigo, "motivo": f"Cidade não encontrada: {item['cidade'] or '(vazia)'}."})
                continue
            if not (item["preco_venda"] or item["preco_locacao"] or item["preco_temporada"]):
                manter.add(chave)
                res.ignorados.append({"codigo": codigo, "motivo": "Sem preço de venda, locação ou temporada."})
                continue
            aceitos += 1
            manter.add(chave)
            tipo = self.resolvedor.tipo(item["tipo"])
            bairro = self.resolvedor.bairro(cidade, item["bairro"])
            valores = self._valores(item, tipo, cidade, bairro, self._ad_type(item["destaque"], contagem))
            planos.append((existentes.get(chave), valores, self._fotos(item), self._features(item), self._taxas(item)))

        excluir = [p for k, p in existentes.items() if k not in manter and p.deleted_at is None] + repetidos
        self._comparar(planos, res)
        res.excluidos = [p.reference_code for p in excluir]
        if not simular:
            self._gravar(planos, excluir)
        return res

    def _comparar(self, planos, res):
        ids = [p.pk for p, *_ in planos if p is not None]
        self.fotos_atuais, self.features_atuais, self.taxas_atuais = {}, {}, {}
        for f in PropertyPhoto.objects.filter(property_id__in=ids).order_by("sort_order", "created_at"):
            self.fotos_atuais.setdefault(f.property_id, []).append(f)
        for pid, fid in Property.features.through.objects.filter(property_id__in=ids).values_list("property_id", "feature_id"):
            self.features_atuais.setdefault(pid, set()).add(fid)
        for t in PropertyFee.objects.filter(property_id__in=ids):
            self.taxas_atuais.setdefault(t.property_id, []).append((t.description, t.amount))
        self.mudancas = {}
        for prop, valores, fotos, features, taxas in planos:
            if prop is None:
                res.novos.append(valores["reference_code"])
                continue
            campos = [c for c in COMPARADOS if self._atual(prop, c) != self._novo(valores[c])]
            if [(f.source_url, f.is_cover) for f in self.fotos_atuais.get(prop.pk, [])] != [(f["url"], f["capa"]) for f in fotos]:
                campos.append("fotos")
            if self.features_atuais.get(prop.pk, set()) != set(features):
                campos.append("caracteristicas")
            if sorted(self.taxas_atuais.get(prop.pk, [])) != sorted((t["description"], t["amount"]) for t in taxas):
                campos.append("taxas")
            self.mudancas[prop.pk] = campos
            if campos:
                res.alterados.append({"codigo": prop.reference_code, "campos": campos})
            else:
                res.iguais += 1

    @staticmethod
    def _atual(prop, campo):
        if campo in ("property_type", "city", "neighborhood"):
            return getattr(prop, f"{campo}_id")
        return getattr(prop, campo)

    @staticmethod
    def _novo(valor):
        return getattr(valor, "pk", valor)

    # --------------------------------------------------------------- escrita
    def _gravar(self, planos, excluir):
        agora = timezone.now()
        slugs = set(Property.objects.values_list("slug", flat=True))
        novos, alterados, com_fotos, com_features, com_taxas = [], [], [], [], []
        for prop, valores, fotos, features, taxas in planos:
            if prop is None:
                prop = Property(advertiser=self.advertiser, **valores, published_at=agora)
                prop.slug = self._slug(f"{valores['title']} {valores['reference_code']}", slugs)
                novos.append(prop)
                mudou = ["fotos", "caracteristicas", "taxas"]
            else:
                mudou = self.mudancas.get(prop.pk, [])
                if not mudou:
                    continue
                for c, v in valores.items():
                    setattr(prop, c, v)
                if not prop.slug:
                    prop.slug = self._slug(f"{valores['title']} {valores['reference_code']}", slugs)
                alterados.append(prop)
            prop.imported_at = agora
            prop.updated_at = agora
            if "fotos" in mudou:
                com_fotos.append((prop, fotos))
            if "caracteristicas" in mudou:
                com_features.append((prop, features))
            if "taxas" in mudou:
                com_taxas.append((prop, taxas))

        with transaction.atomic():
            if novos:
                Property.objects.bulk_create(novos, batch_size=300)
            if alterados:
                Property.objects.bulk_update(alterados, (*CAMPOS, "slug", "imported_at", "updated_at"), batch_size=200)
            self._gravar_fotos(com_fotos)
            if com_features:
                through = Property.features.through
                through.objects.filter(property_id__in=[p.pk for p, _ in com_features]).delete()
                through.objects.bulk_create(
                    [through(property_id=p.pk, feature_id=fid) for p, ids in com_features for fid in ids], batch_size=1000, ignore_conflicts=True
                )
            if com_taxas:
                PropertyFee.objects.filter(property_id__in=[p.pk for p, _ in com_taxas]).delete()
                PropertyFee.objects.bulk_create([PropertyFee(property_id=p.pk, **t) for p, ts in com_taxas for t in ts], batch_size=1000)
            if excluir:
                Property.objects.filter(pk__in=[p.pk for p in excluir]).hard_delete()

    def _gravar_fotos(self, com_fotos):
        """Mantém a linha (e a miniatura) das fotos que continuam; cria as novas e remove as que saíram."""
        novas, alteradas, remover = [], [], []
        for prop, fotos in com_fotos:
            atuais = {f.source_url: f for f in self.fotos_atuais.get(prop.pk, [])}
            urls = set()
            for ordem, f in enumerate(fotos, 1):
                urls.add(f["url"])
                atual = atuais.get(f["url"])
                if atual is None:
                    novas.append(PropertyPhoto(property_id=prop.pk, source_url=f["url"], sort_order=ordem, is_cover=f["capa"]))
                elif atual.sort_order != ordem or atual.is_cover != f["capa"]:
                    atual.sort_order, atual.is_cover = ordem, f["capa"]
                    alteradas.append(atual)
            remover += [f.pk for url, f in atuais.items() if url not in urls]
        if remover:
            PropertyPhoto.objects.filter(pk__in=remover).delete()
        if alteradas:
            PropertyPhoto.objects.bulk_update(alteradas, ["sort_order", "is_cover"], batch_size=500)
        if novas:
            PropertyPhoto.objects.bulk_create(novas, batch_size=1000)

    @staticmethod
    def _slug(texto, slugs):
        base = slugify(texto)[:220] or "imovel"
        slug, n = base, 2
        while slug in slugs:
            sufixo = f"-{n}"
            slug = f"{base[: 220 - len(sufixo)]}{sufixo}"
            n += 1
        slugs.add(slug)
        return slug
