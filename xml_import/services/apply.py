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
from xml_import.formats.base import normalize_name
from xml_import.services.cancellation import check_cancelled
from xml_import.services.resolver import Resolver

FIELDS = (
    "reference_code",
    "status",
    "is_active",
    "ad_type",
    "property_type",
    "city",
    "neighborhood",
    "neighborhood_name",
    "is_in_condominium",
    "bedrooms",
    "suites",
    "bathrooms",
    "parking_spaces",
    "built_area",
    "total_area",
    "description",
    "sale_price",
    "rent_price",
    "seasonal_rent_price",
    "title",
    "deleted_at",
)
# Campos comparados para decidir se o imóvel mudou (o título deriva deles).
COMPARED_FIELDS = tuple(f for f in FIELDS if f not in ("status", "title"))
# De quantos em quantos imóveis o cancelamento é checado durante a comparação.
CANCEL_CHECK_EVERY = 200


@dataclass
class Result:
    """O que entrou, mudou, saiu e foi ignorado. ``summary``/``details`` usam as chaves lidas pelo painel."""

    total_feed: int = 0
    created: list = field(default_factory=list)
    changed: list = field(default_factory=list)
    unchanged: int = 0
    deleted: list = field(default_factory=list)
    ignored: list = field(default_factory=list)

    def summary(self):
        return {
            "total_feed": self.total_feed,
            "novos": len(self.created),
            "alterados": len(self.changed),
            "iguais": self.unchanged,
            "excluidos": len(self.deleted),
            "ignorados": len(self.ignored),
        }

    def details(self, limit=500):
        return {
            **self.summary(),
            "codigos_novos": self.created[:limit],
            "codigos_alterados": self.changed[:limit],
            "codigos_excluidos": self.deleted[:limit],
            "ignorados_lista": self.ignored[:limit],
        }


def _dec(value):
    return Decimal(value) if value not in (None, "") else None


class FeatureCatalog:
    """Características por nome (criadas na hora quando o feed traz uma nova)."""

    def __init__(self):
        self.cache = {}
        for f in Feature.objects.order_by("created_at"):
            self.cache.setdefault((f.scope, normalize_name(f.name)), f)

    def get(self, scope, name):
        # Sem acento e sem maiúsculas: "Quadra de tênis" do feed casa com "Quadra de tenis" do catálogo.
        key = (scope, normalize_name(name))
        if key not in self.cache:
            self.cache[key] = Feature.objects.create(
                scope=scope,
                name=name.strip()[:100],
                slug=unique_slug(Feature, name, max_length=100, scope={"scope": scope}),
                sort_order=99,
            )
        return self.cache[key]


class Applier:
    def __init__(self, advertiser):
        self.advertiser = advertiser
        self.resolver = Resolver(advertiser)
        self.features = FeatureCatalog()
        self.property_limit = advertiser.effective_property_limit or 0
        self.photo_limit = advertiser.effective_photo_limit or 0
        self.featured_limit = advertiser.effective_featured_limit or 0
        self.super_featured_limit = advertiser.super_featured_limit or 0

    # ------------------------------------------------------------ montagem
    def _ad_type(self, featured, counters):
        if featured == 2 and counters["super"] < self.super_featured_limit:
            counters["super"] += 1
            return Property.AdType.SUPER_FEATURED
        if featured >= 1 and counters["featured"] < self.featured_limit:
            counters["featured"] += 1
            return Property.AdType.FEATURED
        return Property.AdType.NORMAL

    def _photos(self, item):
        photos = item["fotos"][: self.photo_limit] if self.photo_limit else item["fotos"]
        seen, out = set(), []
        for p in photos:
            if p["url"] not in seen:
                seen.add(p["url"])
                out.append({"url": p["url"], "capa": p["capa"]})
        if out:
            cover = next((i for i, p in enumerate(out) if p["capa"]), 0)
            for i, p in enumerate(out):
                p["capa"] = i == cover
        return out

    def _features(self, item):
        ids = []
        for scope, names in (
            (Feature.Scope.PROPERTY, item["infra_imovel"]),
            (Feature.Scope.CONDOMINIUM, item["infra_condominio"]),
        ):
            for name in names:
                f = self.features.get(scope, name)
                if f.pk not in ids:
                    ids.append(f.pk)
        return ids

    @staticmethod
    def _fees(item):
        return [
            {
                "description": t["descricao"][:150],
                "amount": Decimal(t["valor"]),
                "period": PropertyFee.Period.YEARLY
                if "iptu" in t["descricao"].lower()
                else PropertyFee.Period.MONTHLY,
                "notes": (t.get("obs") or "")[:300],
            }
            for t in item["taxas"]
        ]

    def _values(self, item, property_type, city, neighborhood, ad_type):
        values = {
            "reference_code": item["codigo"][:45],
            "status": Property.Status.PUBLISHED,
            "is_active": True,
            "ad_type": ad_type,
            "property_type": property_type,
            "city": city,
            "neighborhood": neighborhood,
            "neighborhood_name": "" if neighborhood else item["bairro"][:120],
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
        values["title"] = PropertyService.build_title({**values, "title": None, "slug": None})
        return values

    # ------------------------------------------------------------- execução
    def run(self, properties, simulate=False, cancel_check=None):
        """
        Compara o feed normalizado com o banco e aplica (ou só calcula, em simulação)

        Args:
            properties: lista de imóveis normalizados
            simulate: ``True`` não grava nada
            cancel_check: consulta de cancelamento (ver ``cancellation.check_cancelled``); checada a cada
                ``CANCEL_CHECK_EVERY`` imóveis e antes de gravar, nunca durante a gravação

        Returns:
            ``Result`` com o que entrou, mudou, saiu e foi ignorado
        """
        result = Result(total_feed=len(properties))
        if not properties:
            return result
        blocked = {
            c.lower()
            for c in RejectedProperty.objects.filter(advertiser=self.advertiser).values_list(
                "property_reference_code", flat=True
            )
        }
        existing, duplicates = {}, []
        # Ativos primeiro: com o mesmo código, fica o ativo mais antigo; os demais são excluídos.
        for prop in Property.objects.filter(advertiser=self.advertiser).order_by(
            F("deleted_at").asc(nulls_first=True), "created_at"
        ):
            key = prop.reference_code.strip().lower()
            if key in existing:
                duplicates.append(prop)
            else:
                existing[key] = prop

        counters = {"featured": 0, "super": 0}
        keep, seen, accepted = set(), set(), 0
        plans = []  # (prop, values, photos, features, fees)
        for n, item in enumerate(properties):
            if n % CANCEL_CHECK_EVERY == 0:
                check_cancelled(cancel_check)
            code = item["codigo"].strip()
            key = code.lower()
            if not code:
                result.ignored.append({"codigo": "", "motivo": "Imóvel sem código."})
                continue
            if key in seen:
                result.ignored.append({"codigo": code, "motivo": "Código repetido no feed."})
                continue
            seen.add(key)
            if self.property_limit and accepted >= self.property_limit:
                result.ignored.append(
                    {
                        "codigo": code,
                        "motivo": f"Acima do limite do plano ({self.property_limit} imóveis).",
                    }
                )
                continue
            if key in blocked:
                result.ignored.append({"codigo": code, "motivo": "Barrado pela moderação."})
                continue
            city = self.resolver.city(item["cidade"], item["uf"])
            if city is None:
                # Mantém o imóvel que já existe; a vaga do plano não é consumida.
                keep.add(key)
                result.ignored.append(
                    {
                        "codigo": code,
                        "motivo": f"Cidade não encontrada: {item['cidade'] or '(vazia)'}.",
                    }
                )
                continue
            if not (item["preco_venda"] or item["preco_locacao"] or item["preco_temporada"]):
                keep.add(key)
                result.ignored.append(
                    {"codigo": code, "motivo": "Sem preço de venda, locação ou temporada."}
                )
                continue
            accepted += 1
            keep.add(key)
            property_type = self.resolver.property_type(item["tipo"])
            neighborhood = self.resolver.neighborhood(city, item["bairro"])
            values = self._values(
                item, property_type, city, neighborhood, self._ad_type(item["destaque"], counters)
            )
            plans.append(
                (
                    existing.get(key),
                    values,
                    self._photos(item),
                    self._features(item),
                    self._fees(item),
                )
            )

        to_delete = [
            p for k, p in existing.items() if k not in keep and p.deleted_at is None
        ] + duplicates
        self._compare(plans, result)
        result.deleted = [p.reference_code for p in to_delete]
        if not simulate:
            check_cancelled(
                cancel_check
            )  # último ponto seguro: a gravação é atômica e não é interrompida
            self._save(plans, to_delete)
        return result

    def _compare(self, plans, result):
        ids = [p.pk for p, *_ in plans if p is not None]
        self.current_photos, self.current_features, self.current_fees = {}, {}, {}
        for p in PropertyPhoto.objects.filter(property_id__in=ids).order_by(
            "sort_order", "created_at"
        ):
            self.current_photos.setdefault(p.property_id, []).append(p)
        for pid, fid in Property.features.through.objects.filter(property_id__in=ids).values_list(
            "property_id", "feature_id"
        ):
            self.current_features.setdefault(pid, set()).add(fid)
        for t in PropertyFee.objects.filter(property_id__in=ids):
            self.current_fees.setdefault(t.property_id, []).append((t.description, t.amount))
        self.changes = {}
        for prop, values, photos, features, fees in plans:
            if prop is None:
                result.created.append(values["reference_code"])
                continue
            fields = [f for f in COMPARED_FIELDS if self._current(prop, f) != self._new(values[f])]
            if [(p.source_url, p.is_cover) for p in self.current_photos.get(prop.pk, [])] != [
                (p["url"], p["capa"]) for p in photos
            ]:
                fields.append("fotos")
            if self.current_features.get(prop.pk, set()) != set(features):
                fields.append("caracteristicas")
            if sorted(self.current_fees.get(prop.pk, [])) != sorted(
                (t["description"], t["amount"]) for t in fees
            ):
                fields.append("taxas")
            self.changes[prop.pk] = fields
            if fields:
                result.changed.append({"codigo": prop.reference_code, "campos": fields})
            else:
                result.unchanged += 1

    @staticmethod
    def _current(prop, field_name):
        if field_name in ("property_type", "city", "neighborhood"):
            return getattr(prop, f"{field_name}_id")
        return getattr(prop, field_name)

    @staticmethod
    def _new(value):
        return getattr(value, "pk", value)

    # --------------------------------------------------------------- escrita
    def _save(self, plans, to_delete):
        now = timezone.now()
        slugs = set(Property.objects.values_list("slug", flat=True))
        created, changed, with_photos, with_features, with_fees = [], [], [], [], []
        for prop, values, photos, features, fees in plans:
            if prop is None:
                prop = Property(advertiser=self.advertiser, **values, published_at=now)
                prop.slug = self._slug(f"{values['title']} {values['reference_code']}", slugs)
                created.append(prop)
                changed_fields = ["fotos", "caracteristicas", "taxas"]
            else:
                changed_fields = self.changes.get(prop.pk, [])
                if not changed_fields:
                    continue
                for name, value in values.items():
                    setattr(prop, name, value)
                if not prop.slug:
                    prop.slug = self._slug(f"{values['title']} {values['reference_code']}", slugs)
                changed.append(prop)
            prop.imported_at = now
            prop.updated_at = now
            if "fotos" in changed_fields:
                with_photos.append((prop, photos))
            if "caracteristicas" in changed_fields:
                with_features.append((prop, features))
            if "taxas" in changed_fields:
                with_fees.append((prop, fees))

        with transaction.atomic():
            if created:
                Property.objects.bulk_create(created, batch_size=300)
            if changed:
                Property.objects.bulk_update(
                    changed, (*FIELDS, "slug", "imported_at", "updated_at"), batch_size=200
                )
            self._save_photos(with_photos)
            if with_features:
                through = Property.features.through
                through.objects.filter(property_id__in=[p.pk for p, _ in with_features]).delete()
                through.objects.bulk_create(
                    [
                        through(property_id=p.pk, feature_id=fid)
                        for p, ids in with_features
                        for fid in ids
                    ],
                    batch_size=1000,
                    ignore_conflicts=True,
                )
            if with_fees:
                PropertyFee.objects.filter(property_id__in=[p.pk for p, _ in with_fees]).delete()
                PropertyFee.objects.bulk_create(
                    [PropertyFee(property_id=p.pk, **t) for p, ts in with_fees for t in ts],
                    batch_size=1000,
                )
            if to_delete:
                Property.objects.filter(pk__in=[p.pk for p in to_delete]).hard_delete()

    def _save_photos(self, with_photos):
        """Mantém a linha (e a miniatura) das fotos que continuam; cria as novas e remove as que saíram."""
        new_photos, updated, to_remove = [], [], []
        for prop, photos in with_photos:
            current = {p.source_url: p for p in self.current_photos.get(prop.pk, [])}
            urls = set()
            for order, p in enumerate(photos, 1):
                urls.add(p["url"])
                existing_photo = current.get(p["url"])
                if existing_photo is None:
                    new_photos.append(
                        PropertyPhoto(
                            property_id=prop.pk,
                            source_url=p["url"],
                            sort_order=order,
                            is_cover=p["capa"],
                        )
                    )
                elif existing_photo.sort_order != order or existing_photo.is_cover != p["capa"]:
                    existing_photo.sort_order, existing_photo.is_cover = order, p["capa"]
                    updated.append(existing_photo)
            to_remove += [p.pk for url, p in current.items() if url not in urls]
        if to_remove:
            PropertyPhoto.objects.filter(pk__in=to_remove).delete()
        if updated:
            PropertyPhoto.objects.bulk_update(updated, ["sort_order", "is_cover"], batch_size=500)
        if new_photos:
            PropertyPhoto.objects.bulk_create(new_photos, batch_size=1000)

    @staticmethod
    def _slug(text, slugs):
        base = slugify(text)[:220] or "imovel"
        slug, n = base, 2
        while slug in slugs:
            suffix = f"-{n}"
            slug = f"{base[: 220 - len(suffix)]}{suffix}"
            n += 1
        slugs.add(slug)
        return slug
