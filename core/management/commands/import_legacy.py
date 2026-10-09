"""import_legacy — importa catálogos, portais e os imóveis de um anunciante do
banco PHP legado (MySQL 5.7, acessado direto via MySQLdb com ``DB_PORTAL_ANTIGO_*``) para os models
novos. Idempotente: tudo é casado por ``legacy_id``. Imóvel que a importação XML já criou para
o anunciante (mesmo código, sem ``legacy_id``) é mantido como está e só ganha o ``legacy_id``:
o feed é mais recente que o legado.

Uso::

    python manage.py import_legacy --client-id 5
    python manage.py import_legacy --client-id 5 --password 'Senha@123'
    python manage.py import_legacy --all                    # todos os clientes do legado
    python manage.py import_legacy --all --from-client 300  # retoma a partir de um Id_Cliente
    python manage.py import_legacy --all --skip-logos --skip-photos
    python manage.py import_legacy --all --skip-properties   # só o cadastro dos clientes, sem imóveis

Os imóveis entram em lote (poucas consultas por cliente, não por imóvel): com o banco
remoto, cada consulta custa ~200 ms. As fotos são só links externos; a miniatura da
capa é gerada depois, à parte, por ``generate_cover_thumbnails``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import secrets
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import (
    Advertiser,
    AdvertiserCity,
    AdvertiserIntegration,
    City,
    Feature,
    Integrator,
    Neighborhood,
    Plan,
    Portal,
    PortalCity,
    PortalMenuItem,
    Property,
    PropertyFee,
    PropertyPhoto,
    PropertyType,
    State,
    User,
)
from core.modules.property.service.property_service import PropertyService
from core.services import grant_advertiser_access, unique_slug
from core.services.images import download
from core.services.public_cache import invalidation_batch

LEGACY_FILES_BASE = "https://www.petropolisimoveis.com/"

PORTAL_DEFAULTS = {
    1: {
        "slug": "petropolis",
        "main_city": 1,
        "show_city_filter": True,
        "seo_title": "Petrópolis Imóveis - Casas, Apartamentos em Petrópolis",
        "seo_description": "Petrópolis Imóveis - O maior portal de classificados de imóveis e imobiliárias de Petrópolis, Casas, Apartamentos em Itaipava e Petrópolis.",
        "seo_keywords": "Casa Petrópolis, Casa Itaipava, Itaipava venda, imoveis na serra, Apartamento Petrópolis, imobiliarias em petropolis, casas a venda em petropolis",
        "about_text": "O Petrópolis Imóveis é um portal de classificados de imóveis focado em Petrópolis e arredores.",
        "facebook_url": "https://www.facebook.com/petropolisimoveis/",
        "instagram_url": "https://www.instagram.com/petropolisimoveis/",
        "ga4_measurement_id": "G-CE60MVTX4W",
        "realtors_page_slug": "imobiliarias-em-petropolis",
        "primary_color": "#204860",
        "secondary_color": "#0078a8",
    },
    2: {
        "slug": "teresopolis",
        "main_city": 5,
        "show_city_filter": False,
        "seo_title": "Teresópolis Imóveis - Casas, Apartamentos em Teresópolis",
        "seo_description": "Teresópolis Imóveis - Portal de classificados de imóveis e imobiliárias de Teresópolis.",
        "seo_keywords": "Casa Teresópolis, Apartamento Teresópolis, imobiliarias em teresopolis",
        "about_text": "O Teresópolis Imóveis é um portal de classificados de imóveis focado em Teresópolis e região serrana.",
        "realtors_page_slug": "imobiliarias-em-teresopolis",
    },
    3: {
        "slug": "juizdefora",
        "main_city": 6,
        "show_city_filter": False,
        "seo_title": "Juiz de Fora Imóveis - Casas, Apartamentos em Juiz de Fora",
        "seo_description": "Juiz de Fora Imóveis - Portal de classificados de imóveis e imobiliárias de Juiz de Fora.",
        "seo_keywords": "Apartamento Juiz de Fora, Casa Juiz de Fora, imobiliarias em juiz de fora",
        "about_text": "O Juiz de Fora Imóveis é um portal de classificados de imóveis focado em Juiz de Fora e Zona da Mata.",
        "realtors_page_slug": "imobiliarias-em-juiz-de-fora",
    },
    4: {
        "slug": "novafriburgo",
        "main_city": 7,
        "show_city_filter": False,
        "seo_title": "Nova Friburgo Imóveis - Casas, Apartamentos em Nova Friburgo",
        "seo_description": "Nova Friburgo Imóveis - Portal de classificados de imóveis e imobiliárias de Nova Friburgo.",
        "seo_keywords": "Casa Nova Friburgo, Apartamento Nova Friburgo, imobiliarias em nova friburgo",
        "about_text": "O Nova Friburgo Imóveis é um portal de classificados de imóveis focado em Nova Friburgo e distritos.",
        "realtors_page_slug": "imobiliarias-em-nova-friburgo",
    },
    5: {
        "slug": "serra",
        "main_city": 1,
        "show_city_filter": True,
        "seo_title": "Serra Imóveis - Imóveis na Região Serrana do Rio",
        "seo_description": "Serra Imóveis - Casas, apartamentos, sítios e terrenos em Petrópolis, Teresópolis, Nova Friburgo e toda a região serrana.",
        "seo_keywords": "imoveis na serra, casa na serra, sítio na serra, Petrópolis, Teresópolis, Nova Friburgo",
        "about_text": "O Serra Imóveis reúne os anúncios dos portais Petrópolis, Teresópolis, Juiz de Fora e Nova Friburgo Imóveis em um só lugar.",
        "realtors_page_slug": "imobiliarias-na-serra",
    },
}

MENU_PADRAO = [
    ("Início", "/"),
    ("Imóveis", "/imoveis"),
    ("Favoritos", "/favoritos"),
    ("Imobiliárias", "/imobiliarias"),
    ("Planos", "/planos"),
    ("Blog", "/blog"),
    ("Contato", "/contato"),
]

ADVERTISER_TYPES = {1: Advertiser.Type.OWNER, 2: Advertiser.Type.BROKER, 3: Advertiser.Type.AGENCY}
LEGACY_TZ = ZoneInfo("America/Sao_Paulo")


def md5_upper(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()  # noqa: S324 - convenção do front


def to_int(value, default=0):
    try:
        return int(str(value).strip() or default)
    except (TypeError, ValueError):
        return default


def to_decimal(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number > 0 else None


def to_datetime(value):
    """Datas do legado são naive no horário de São Paulo."""
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=LEGACY_TZ)


def to_bool(value):
    return str(value).strip() in {"1", "True", "true"}


def split_list(value):
    return [p.strip() for p in str(value or "").split(";") if p.strip()]




class Command(BaseCommand):
    help = "Importa catálogos, portais e os imóveis de um anunciante do banco legado (conexão 'legacy')."

    def add_arguments(self, parser):
        parser.add_argument("--client-id", type=int, help="Id_Cliente no banco legado.")
        parser.add_argument("--all", action="store_true", help="Importa todos os clientes do legado e seus imóveis.")
        parser.add_argument("--from-client", type=int, default=0, help="Com --all: começa deste Id_Cliente (retomar).")
        parser.add_argument("--to-client", type=int, default=0, help="Com --all: para neste Id_Cliente (0 = até o fim).")
        parser.add_argument("--password", help="Senha inicial do usuário (só com --client-id; gerada se omitida).")
        parser.add_argument("--skip-photos", action="store_true", help="Não registra os links das fotos.")
        parser.add_argument("--skip-logos", action="store_true", help="Não baixa os logos dos anunciantes.")
        parser.add_argument("--limit", type=int, default=0, help="Importa só os N primeiros imóveis de cada cliente (teste).")
        parser.add_argument("--skip-properties", action="store_true", help="Só o cadastro do cliente (usuário, integração, cidades, logo); não importa imóveis.")

    # ------------------------------------------------------------------ infra
    def handle(self, *args, **options):
        cfg = settings.LEGACY_DB
        if not cfg["host"]:
            raise CommandError("Banco legado não configurado: defina DB_PORTAL_ANTIGO_* no .env.")
        self.legacy = None
        self.conectar_legado()
        if not options["client_id"] and not options["all"]:
            raise CommandError("Informe --client-id ou --all.")
        self.skip_photos = options["skip_photos"]
        self.skip_logos = options["skip_logos"]
        self.skip_properties = options["skip_properties"]
        self.stats = {}
        self.totais = {"criados": 0, "atualizados": 0, "vinculados": 0, "pulados": 0, "fotos": 0}
        senha = None
        advertiser = None

        # Gravações em lote não disparam sinais: no fim o cache público é limpo inteiro e o site avisado.
        with invalidation_batch(user="import_legacy", everything=True, wait_site=True) as cache:
            self.import_states()
            self.import_cities()
            self.import_neighborhoods()
            self.import_property_types()
            self.import_features()
            self.import_plans()
            self.import_integrators()
            self.import_portals()
            self.carregar_caches()
            if options["all"]:
                self.import_all(options["from_client"], options["to_client"], options["limit"])
            else:
                advertiser, senha = self.import_advertiser(options["client_id"], options["password"])
                if not self.skip_properties:
                    self.import_properties(advertiser, options["limit"])

        self.stats["imóveis (total)"] = (
            f"{self.totais['criados']} criados, {self.totais['atualizados']} atualizados, "
            f"{self.totais['vinculados']} já vindos do XML, {self.totais['pulados']} pulados, "
            f"{self.totais['fotos']} links de foto novos"
        )
        site = cache.get("site")
        if site is None:
            self.stats["cache"] = "API limpa; site não avisado"
        elif site["ok"]:
            self.stats["cache"] = "API limpa; site avisado"
        else:
            self.stats["cache"] = f"API limpa; aviso ao site falhou: {site['error']}"
        self.stdout.write(self.style.SUCCESS("\nResumo:"))
        for nome, valor in self.stats.items():
            self.stdout.write(f"  {nome}: {valor}")
        if senha and advertiser:
            self.stdout.write(
                self.style.WARNING(
                    f"\nUsuário do anunciante: {advertiser.email}  senha inicial: {senha}  (gravada no padrão MD5-upper do front)"
                )
            )

    def import_all(self, from_client, to_client, limit):
        """
        Importa todos os clientes do legado, um por vez, sem parar em erro de um deles

        Args:
            from_client: primeiro Id_Cliente a importar (retomada)
            to_client: último Id_Cliente (0 = sem limite)
            limit: máximo de imóveis por cliente (0 = todos)
        """
        ids = [r["Id_Cliente"] for r in self.rows("SELECT Id_Cliente FROM cliente WHERE Id_Cliente >= %s ORDER BY Id_Cliente", [from_client])]
        if to_client:
            ids = [i for i in ids if i <= to_client]
        falhas = []
        inicio = time.monotonic()
        for n, cid in enumerate(ids, 1):
            t = time.monotonic()
            antes = dict(self.totais)
            try:
                # O legado derruba conexões ociosas durante as gravações no banco novo; uma nova por cliente evita a espera.
                self.conectar_legado()
                advertiser, _ = self.import_advertiser(cid, None, mostrar_senha=False)
                if not self.skip_properties:
                    self.import_properties(advertiser, limit)
                feitos = sum(self.totais[k] - antes[k] for k in ("criados", "atualizados", "vinculados"))
                decorrido = time.monotonic() - inicio
                restante = decorrido / n * (len(ids) - n)
                self.stdout.write(
                    f"[{n}/{len(ids)}] cliente {cid} {advertiser.name[:40]}: {'só cadastro' if self.skip_properties else f'{feitos} imóveis'} em {time.monotonic() - t:.0f}s "
                    f"(faltam ~{restante / 60:.0f} min)"
                )
            except Exception as e:  # noqa: BLE001 - um cliente com problema não interrompe os demais
                falhas.append((cid, str(e)[:200]))
                self.stdout.write(self.style.ERROR(f"[{n}/{len(ids)}] cliente {cid}: FALHOU ({str(e)[:200]})"))
        self.stats["clientes"] = f"{len(ids) - len(falhas)} importados, {len(falhas)} com falha"
        for cid, erro in falhas:
            self.stdout.write(self.style.ERROR(f"  falha no cliente {cid}: {erro}"))

    def carregar_caches(self):
        """Carrega uma vez o que a importação em lote consulta muito (características e slugs)."""
        self.features_cache = {(f.scope, f.name.strip().lower()): f for f in Feature.objects.all()}
        self.slugs_imoveis = set(Property.objects.values_list("slug", flat=True))
        self.tipos = {t.legacy_id: t for t in PropertyType.objects.exclude(legacy_id=None)}
        self.cidades = {c.legacy_id: c for c in City.objects.exclude(legacy_id=None)}
        self.bairros = {b.legacy_id: b for b in Neighborhood.objects.exclude(legacy_id=None)}

    def slug_imovel(self, texto):
        base = slugify(texto)[:220] or "imovel"
        slug, n = base, 2
        while slug in self.slugs_imoveis:
            sufixo = f"-{n}"
            slug = f"{base[: 220 - len(sufixo)]}{sufixo}"
            n += 1
        self.slugs_imoveis.add(slug)
        return slug

    def conectar_legado(self):
        import MySQLdb

        cfg = settings.LEGACY_DB
        if self.legacy is not None:
            with contextlib.suppress(Exception):
                self.legacy.close()
        ultimo_erro = None
        for tentativa in range(1, 6):
            try:
                self.legacy = MySQLdb.connect(
                    host=cfg["host"],
                    port=cfg["port"],
                    user=cfg["user"],
                    passwd=cfg["password"],
                    db=cfg["name"],
                    charset="utf8mb4",
                    connect_timeout=20,
                    # Conexão morta deve falhar rápido em vez de travar a importação.
                    read_timeout=120,
                    write_timeout=60,
                )
                return
            except MySQLdb.OperationalError as e:
                ultimo_erro = e
                self.log(self.style.WARNING(f"Legado indisponível ({e}); nova tentativa em {10 * tentativa}s"))
                time.sleep(10 * tentativa)
        raise CommandError(f"Não foi possível conectar ao banco legado: {ultimo_erro}")

    def rows(self, sql, params=None):
        """Consulta o legado; reconecta e tenta de novo se o servidor derrubar a conexão."""
        import MySQLdb

        for tentativa in (1, 2, 3):
            try:
                self.legacy.ping(True)
                cur = self.legacy.cursor()
                try:
                    cur.execute(sql, params or [])
                    cols = [c[0] for c in cur.description]
                    return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]
                finally:
                    cur.close()
            except (MySQLdb.OperationalError, MySQLdb.InterfaceError) as e:
                if tentativa == 3:
                    raise
                self.log(self.style.WARNING(f"Conexão com o legado caiu ({e}); reconectando..."))
                time.sleep(2 * tentativa)
                self.conectar_legado()
        return []

    def log(self, msg):
        self.stdout.write(msg)

    # -------------------------------------------------------------- catálogos
    def import_states(self):
        criados = 0
        for r in self.rows("SELECT Id_UF, Descricao FROM UF"):
            _, created = State.objects.get_or_create(code=r["Id_UF"].upper(), defaults={"name": r["Descricao"]})
            criados += created
        self.stats["states"] = f"{criados} criados"

    def import_cities(self):
        criados = 0
        for r in self.rows("SELECT Id_Cidade, Descricao, Id_UF, Regras FROM cidade"):
            state = State.objects.get(code=(r["Id_UF"] or "RJ").upper())
            city = City.objects.filter(legacy_id=r["Id_Cidade"]).first()
            if city is None:
                city = City.objects.filter(state=state, name=r["Descricao"]).first()
            if city is None:
                city = City.objects.create(
                    legacy_id=r["Id_Cidade"],
                    state=state,
                    name=r["Descricao"],
                    slug=unique_slug(City, r["Descricao"], max_length=120, scope={"state": state}),
                    import_aliases=split_list(r["Regras"]),
                )
                criados += 1
            elif city.legacy_id is None:
                city.legacy_id = r["Id_Cidade"]
                city.save(update_fields=["legacy_id"])
        self.stats["cities"] = f"{criados} criadas"

    def import_neighborhoods(self):
        """Bairros em lote: resolve tudo em memória e grava com bulk_create (banco remoto)."""
        cidades = {c.legacy_id: c for c in City.objects.exclude(legacy_id=None)}
        existentes = list(Neighborhood.objects.select_related("city").only("id", "legacy_id", "name", "slug", "city_id"))
        por_legacy = {n.legacy_id for n in existentes if n.legacy_id}
        por_nome = {(n.city_id, n.name.lower()): n for n in existentes}
        slugs_por_cidade = {}
        for n in existentes:
            slugs_por_cidade.setdefault(n.city_id, set()).add(n.slug)

        novos, religados = [], []
        for r in self.rows("SELECT Id_Bairro, Id_Cidade, Descricao, Regras FROM bairro"):
            city = cidades.get(r["Id_Cidade"])
            nome = (r["Descricao"] or "").strip()
            if city is None or not nome or r["Id_Bairro"] in por_legacy:
                continue
            existente = por_nome.get((city.id, nome.lower()))
            if existente:
                existente.legacy_id = r["Id_Bairro"]
                religados.append(existente)
                por_legacy.add(r["Id_Bairro"])
                continue
            usados = slugs_por_cidade.setdefault(city.id, set())
            base = slugify(nome)[:120] or "bairro"
            slug, k = base, 2
            while slug in usados:
                sufixo = f"-{k}"
                slug = f"{base[: 120 - len(sufixo)]}{sufixo}"
                k += 1
            usados.add(slug)
            novos.append(Neighborhood(legacy_id=r["Id_Bairro"], city=city, name=nome, slug=slug, import_aliases=split_list(r["Regras"])))
            por_nome[(city.id, nome.lower())] = novos[-1]
            por_legacy.add(r["Id_Bairro"])

        Neighborhood.objects.bulk_create(novos, batch_size=200)
        if religados:
            Neighborhood.objects.bulk_update(religados, ["legacy_id"], batch_size=200)
        self.stats["neighborhoods"] = f"{len(novos)} criados, {len(religados)} religados"

    def import_property_types(self):
        criados = 0
        residenciais = {"Casa", "Apartamento", "Cobertura", "Flat", "Fazenda / Sítio", "Chácara", "Kitnet / Conjugado", "Studio"}
        for i, r in enumerate(self.rows("SELECT Id_ImovelTipo, Descricao, Regras, Tipo_MercadoLivre FROM imoveltipo ORDER BY Id_ImovelTipo")):
            nome = (r["Descricao"] or "").strip() or f"Tipo {r['Id_ImovelTipo']}"
            if PropertyType.objects.filter(legacy_id=r["Id_ImovelTipo"]).exists():
                continue
            existente = PropertyType.objects.filter(name=nome).first()
            if existente:
                existente.legacy_id = r["Id_ImovelTipo"]
                existente.save(update_fields=["legacy_id"])
                continue
            PropertyType.objects.create(
                legacy_id=r["Id_ImovelTipo"],
                name=nome,
                slug=unique_slug(PropertyType, nome, max_length=60),
                import_aliases=split_list(r["Regras"]),
                mercadolivre_category=r["Tipo_MercadoLivre"] or "",
                is_residential=nome in residenciais,
                sort_order=i,
            )
            criados += 1
        self.stats["property_types"] = f"{criados} criados"

    def import_features(self):
        criados = 0
        fontes = (
            ("SELECT Id_ImovelInfra AS id, Descricao FROM imovelinfra", Feature.Scope.PROPERTY),
            ("SELECT Id_ImovelInfraCondominio AS id, Descricao FROM imovelinfracondominio", Feature.Scope.CONDOMINIUM),
        )
        for sql, scope in fontes:
            for i, r in enumerate(self.rows(sql)):
                nome = (r["Descricao"] or "").strip()
                if not nome:
                    continue
                feature = self.feature_por_nome(scope, nome, create=False)
                if feature is None:
                    self.criar_feature(scope, nome, legacy_id=r["id"], sort_order=i)
                    criados += 1
                elif feature.legacy_id is None:
                    feature.legacy_id = r["id"]
                    feature.save(update_fields=["legacy_id"])
        self.stats["features"] = f"{criados} criadas"

    def feature_por_nome(self, scope, nome, create=True):
        chave = (scope, nome.strip().lower())
        cache = getattr(self, "features_cache", None)
        if cache is not None and chave in cache:
            return cache[chave]
        feature = Feature.objects.filter(scope=scope, name__iexact=nome.strip()).first()
        if feature is None and create:
            feature = self.criar_feature(scope, nome.strip())
        if cache is not None and feature is not None:
            cache[chave] = feature
        return feature

    def criar_feature(self, scope, nome, legacy_id=None, sort_order=99):
        return Feature.objects.create(
            legacy_id=legacy_id,
            scope=scope,
            name=nome,
            slug=unique_slug(Feature, nome, max_length=100, scope={"scope": scope}),
            sort_order=sort_order,
        )

    def import_plans(self):
        criados = 0
        for i, r in enumerate(self.rows("SELECT * FROM Produto ORDER BY Id_Produto")):
            if Plan.objects.filter(legacy_id=r["Id_Produto"]).exists():
                continue
            nome = (r["Nome"] or "").strip().title().replace("Gratis", "Grátis")
            existente = Plan.objects.filter(legacy_id=None, name__iexact=nome).first()
            if existente:
                existente.legacy_id = r["Id_Produto"]
                existente.save(update_fields=["legacy_id"])
                continue
            Plan.objects.create(
                legacy_id=r["Id_Produto"],
                name=nome,
                slug=unique_slug(Plan, f"{nome} {r['Id_Produto']}" if r["Id_Produto"] == 2 else nome, max_length=60),
                monthly_price=Decimal(to_int(r["Preco"])),
                property_limit=to_int(r["Imoveis"]),
                photo_limit=to_int(r["Fotos"]),
                featured_limit=to_int(r["Destaques"]),
                has_realtor_page=to_bool(r["PaginaImobiliaria"]),
                receives_property_requests=to_bool(r["EncomendaImovel"]),
                has_hotsite=to_bool(r["HotSite"]),
                is_owner_only=r["Id_Produto"] in (1, 2),
                is_recommended=r["Id_Produto"] == 4,
                is_active=r["Id_Produto"] != 2,
                sort_order=i,
            )
            criados += 1
        self.stats["plans"] = f"{criados} criados"

    def import_integrators(self):
        criados = 0
        for r in self.rows("SELECT Id_Integrador, Descricao FROM Integrador"):
            if Integrator.objects.filter(legacy_id=r["Id_Integrador"]).exists():
                continue
            nome = (r["Descricao"] or f"Integrador {r['Id_Integrador']}").strip()
            Integrator.objects.create(legacy_id=r["Id_Integrador"], name=nome, slug=unique_slug(Integrator, nome, max_length=60))
            criados += 1
        self.stats["integrators"] = f"{criados} criados"

    # ---------------------------------------------------------------- portais
    def import_portals(self):
        criados = 0
        cidades = {c.legacy_id: c for c in City.objects.exclude(legacy_id=None)}
        linhas = self.rows("SELECT Id_Portal, Id_PortalCombinado, Portal, Site, Email, Cidades FROM Portal ORDER BY Id_Portal")
        combinados = {}
        for r in linhas:
            defaults = PORTAL_DEFAULTS.get(r["Id_Portal"], {})
            dominio = re.sub(r"^https?://", "", (r["Site"] or "").strip()).strip("/")
            portal = Portal.objects.filter(legacy_id=r["Id_Portal"]).first() or Portal.objects.filter(slug=defaults.get("slug", "")).first()
            ids_cidades = [to_int(x) for x in str(r["Cidades"] or "").split(",") if x.strip()]
            main_city = cidades.get(defaults.get("main_city")) or cidades.get(ids_cidades[0] if ids_cidades else None)
            if main_city is None:
                raise CommandError(f"Portal {r['Portal']}: cidade principal não encontrada.")
            if portal is None:
                portal = Portal.objects.create(
                    legacy_id=r["Id_Portal"],
                    slug=defaults.get("slug") or slugify(r["Portal"]),
                    name=r["Portal"],
                    domain=dominio or f"{slugify(r['Portal'])}.com.br",
                    extra_domains=[dominio.replace("www.", "")] if dominio.startswith("www.") else [],
                    main_city=main_city,
                    show_city_filter=defaults.get("show_city_filter", False),
                    email=r["Email"] or "",
                    phone="(24) 2222-4299",
                    whatsapp="5524922224299",
                    address="Estr. União e Indústria, 9300/12 - Itaipava, Petrópolis - RJ, 25730-735",
                    seo_title=defaults.get("seo_title", r["Portal"]),
                    seo_description=defaults.get("seo_description", r["Portal"]),
                    seo_keywords=defaults.get("seo_keywords", ""),
                    about_text=defaults.get("about_text", ""),
                    facebook_url=defaults.get("facebook_url", ""),
                    instagram_url=defaults.get("instagram_url", ""),
                    ga4_measurement_id=defaults.get("ga4_measurement_id", ""),
                    realtors_page_slug=defaults.get("realtors_page_slug", "imobiliarias"),
                    primary_color=defaults.get("primary_color", ""),
                    secondary_color=defaults.get("secondary_color", ""),
                )
                criados += 1
                for ordem, (label, path) in enumerate(MENU_PADRAO):
                    PortalMenuItem.objects.create(portal=portal, label=label, path=path, sort_order=ordem)
            elif portal.legacy_id is None:
                portal.legacy_id = r["Id_Portal"]
                portal.save(update_fields=["legacy_id"])
            for ordem, cid in enumerate(ids_cidades):
                if cid in cidades:
                    PortalCity.objects.get_or_create(portal=portal, city=cidades[cid], defaults={"sort_order": ordem})
            combinados[portal] = [to_int(x) for x in str(r["Id_PortalCombinado"] or "").split(",") if x.strip()]
        portais = {p.legacy_id: p for p in Portal.objects.exclude(legacy_id=None)}
        for portal, ids in combinados.items():
            outros = [portais[i] for i in ids if i in portais and portais[i].pk != portal.pk]
            if outros:
                portal.combined_portals.set(outros)
        self.stats["portals"] = f"{criados} criados"

    # ------------------------------------------------------------- anunciante
    def import_advertiser(self, client_id, password, mostrar_senha=True):
        linhas = self.rows("SELECT * FROM cliente WHERE Id_Cliente = %s", [client_id])
        if not linhas:
            raise CommandError(f"cliente {client_id} não encontrado no legado.")
        r = linhas[0]
        portal = Portal.objects.filter(legacy_id=r["Id_Portal"]).first() or Portal.objects.get(legacy_id=1)
        plan = Plan.objects.filter(legacy_id=r["Id_Produto"]).first() or Plan.objects.get(legacy_id=1)
        tipo = ADVERTISER_TYPES.get(to_int(r["TipoCliente"]), Advertiser.Type.AGENCY)
        nome = (r["Nome"] or f"Anunciante {client_id}").strip()
        email = (r["Email"] or f"anunciante{client_id}@sem-email.local").strip().lower()
        senha_gerada = None

        with transaction.atomic():
            advertiser = Advertiser.objects.filter(legacy_id=client_id).first()
            if advertiser is None:
                advertiser = Advertiser(legacy_id=client_id, slug=unique_slug(Advertiser, nome, max_length=140))
            advertiser.portal = portal
            advertiser.plan = plan
            advertiser.type = tipo
            advertiser.name = nome
            advertiser.document = re.sub(r"\D", "", r["CNPJ"] or "")[:14]
            advertiser.email = email
            advertiser.phone = r["Telefone"] or ""
            advertiser.phone_secondary = r["Telefone2"] or ""
            advertiser.whatsapp = re.sub(r"\D", "", r["WhatsApp"] or "")
            site = (r["Site"] or "").strip()
            advertiser.website = site if not site or site.startswith("http") else f"https://{site}"
            advertiser.address = r["Endereco"] or ""
            advertiser.creci = r["Creci"] or ""
            advertiser.contact_name = r["Contato"] or ""
            advertiser.responsible_broker = r["CorretorResponsavel"] or ""
            advertiser.notes = r["Observacao"] or ""
            advertiser.coupon = r["Cupon"] or ""
            advertiser.is_published = to_bool(r["Portal"])
            advertiser.accepted_terms_at = timezone.now() if to_bool(r["TermoDeUso"]) else None
            advertiser.notify_by_email = to_bool(r["NotificacaoEmail"]) if r["NotificacaoEmail"] is not None else True
            advertiser.has_hotsite = to_bool(r["HotSite"])
            advertiser.has_realtor_page = to_bool(r["PaginaImobiliaria"])
            advertiser.receives_property_requests = to_bool(r["RecebeEmailEncomendaImovel"])
            advertiser.property_limit = to_int(r["NoImoveis"]) if r["NoImoveis"] not in (None, "") else None
            advertiser.photo_limit = to_int(r["NoFotos"]) if r["NoFotos"] not in (None, "") else None
            advertiser.featured_limit = to_int(r["Destaques"]) if r["Destaques"] not in (None, "") else None
            advertiser.super_featured_limit = to_int(r["SuperDestaques"]) if r["SuperDestaques"] not in (None, "") else None
            advertiser.legacy_password_md5 = (r["Senha"] or "")[:32]

            if advertiser.user_id is None:
                user = User.objects.filter(email=email).first()
                if user is not None and Advertiser.objects.filter(user=user).exclude(pk=advertiser.pk).exists():
                    # Mesmo e-mail em dois clientes do legado: o login fica com o primeiro.
                    self.log(self.style.WARNING(f"  cliente {client_id}: e-mail {email} já pertence a outro anunciante; ficou sem usuário."))
                    user = None
                elif user is None:
                    senha_gerada = password or secrets.token_urlsafe(9)
                    user = User(email=email, name=nome, role=User.Role.USER, is_active=True, email_verified=True)
                    user.set_password(md5_upper(senha_gerada))
                    user.save()
                elif password:
                    senha_gerada = password
                    user.set_password(md5_upper(password))
                    user.save(update_fields=["password"])
                advertiser.user = user
            elif password:
                senha_gerada = password
                advertiser.user.set_password(md5_upper(password))
                advertiser.user.save(update_fields=["password"])

            advertiser.save()
            if advertiser.user_id:
                grant_advertiser_access(advertiser.user)

            integration, _ = AdvertiserIntegration.objects.get_or_create(advertiser=advertiser)
            integration.integrator = Integrator.objects.filter(legacy_id=r["Id_Integrador"]).first()
            integration.xml_url = r["URL_XML"] or ""
            integration.xml_default_url = r["URL_XML_Padrao"] or ""
            integration.api_token = r["TokenGaia"] or ""
            integration.vista_portal_key = r["Vista_ChavePortal"] or ""
            integration.vista_customer_code = r["Vista_CodigoCliente"] or ""
            integration.vista_customer_key = r["Vista_ChaveCliente"] or ""
            integration.vista_api_url = r["Vista_LinkAPI"] or ""
            integration.save_all_images = to_bool(r["SalvarTodasImagens"])
            integration.skip_thumbnails = to_bool(r["NaoSalvarMiniaturas"])
            integration.is_active = bool(integration.xml_url)
            integration.save()

            cidades = getattr(self, "cidades", None) or {c.legacy_id: c for c in City.objects.exclude(legacy_id=None)}
            ja = set(AdvertiserCity.objects.filter(advertiser=advertiser).values_list("city_id", flat=True))
            novas = []
            for c in self.rows("SELECT Id_Cidade FROM clientecidadeportal WHERE Id_Cliente = %s", [client_id]):
                city = cidades.get(c["Id_Cidade"])
                if city and city.pk not in ja:
                    novas.append(AdvertiserCity(advertiser=advertiser, city=city))
                    ja.add(city.pk)
            if novas:
                AdvertiserCity.objects.bulk_create(novas, ignore_conflicts=True)

        if r["Logo"] and not advertiser.logo and not getattr(self, "skip_logos", False):
            conteudo = download(f"{LEGACY_FILES_BASE}LogoClientes/{r['Logo']}")
            if conteudo:
                advertiser.logo.save(f"{advertiser.slug}-{r['Logo']}", ContentFile(conteudo), save=True)
            else:
                self.log(self.style.WARNING("Logo não baixado."))

        self.stats["advertiser"] = f"{advertiser.name} ({advertiser.email})"
        return advertiser, (senha_gerada if mostrar_senha else None)

    # ---------------------------------------------------------------- imóveis
    CAMPOS_IMOVEL = (
        "reference_code", "status", "is_active", "ad_type", "property_type", "city", "neighborhood",
        "neighborhood_name", "is_in_condominium", "bedrooms", "suites", "bathrooms", "parking_spaces",
        "built_area", "total_area", "description", "sale_price", "rent_price", "seasonal_rent_price",
        "photos_checksum", "imported_at", "published_at", "title", "slug", "advertiser",
    )

    def import_properties(self, advertiser, limit):
        """
        Importa os imóveis de um anunciante em lote: o número de consultas não depende de quantos imóveis ele tem

        Args:
            advertiser: anunciante já importado
            limit: máximo de imóveis (0 = todos)
        """
        if not hasattr(self, "tipos"):
            self.carregar_caches()
        sql = "SELECT * FROM imovel WHERE Id_Cliente = %s ORDER BY Id_Imovel"
        if limit:
            sql += f" LIMIT {int(limit)}"
        linhas = self.rows(sql, [advertiser.legacy_id])
        if not linhas:
            self.stats["properties"] = "nenhum imóvel"
            return
        atuais = list(Property.objects.filter(advertiser=advertiser))
        existentes = {p.legacy_id: p for p in atuais if p.legacy_id is not None}
        # A chave única é (anunciante, código), sem diferenciar maiúsculas. Imóvel que a importação XML
        # já criou (sem legacy_id) é a fonte mais recente: fica como está e só recebe o legacy_id.
        por_codigo = {p.reference_code.strip().lower(): p for p in atuais}
        novos, alterados, datas, origem, vinculados = [], [], [], {}, []
        pulados = repetidos = 0
        vistos = set()

        for r in linhas:
            tipo = self.tipos.get(to_int(r["Id_ImovelTipo"])) or self.tipos.get(20)
            city = self.cidades.get(to_int(r["Id_Cidade"]))
            if tipo is None or city is None:
                pulados += 1
                continue
            codigo = (r["ApelidoImovel"] or str(r["Id_Imovel"])).strip()[:45]
            chave = codigo.lower()
            if chave in vistos:
                repetidos += 1  # mesmo código duas vezes no legado: fica o primeiro
                continue
            vistos.add(chave)
            bairro = self.bairros.get(to_int(r["Id_Bairro"]))
            prop = existentes.get(r["Id_Imovel"])
            if prop is None:
                outro = por_codigo.get(chave)
                if outro is not None:
                    if outro.legacy_id is None:
                        outro.legacy_id = r["Id_Imovel"]
                        vinculados.append(outro)
                    else:
                        repetidos += 1  # código já pertence a outro imóvel do legado
                    continue
            novo = prop is None
            if novo:
                prop = Property(legacy_id=r["Id_Imovel"])
            prop.advertiser = advertiser
            prop.reference_code = codigo
            prop.status = Property.Status.PUBLISHED
            prop.is_active = to_bool(r["Ativo"])
            destaque = to_int(r["Destaque"])
            prop.ad_type = Property.AdType.SUPER_FEATURED if destaque >= 2 else Property.AdType.FEATURED if destaque == 1 else Property.AdType.NORMAL
            prop.property_type = tipo
            prop.city = city
            prop.neighborhood = bairro
            prop.neighborhood_name = "" if bairro else (r["Bairro"] or "")
            prop.is_in_condominium = to_bool(r["DentroCondominio"])
            prop.bedrooms = to_int(r["Quarto"])
            prop.suites = to_int(r["Suite"])
            prop.bathrooms = to_int(r["Banheiro"])
            prop.parking_spaces = to_int(r["Garagem"])
            prop.built_area = to_decimal(r["AreaConstruida"])
            prop.total_area = to_decimal(r["AreaTotal"])
            prop.description = (r["Descricao"] or "").strip()
            prop.sale_price = to_decimal(r["PrecoVenda"])
            prop.rent_price = to_decimal(r["PrecoLocacao"])
            prop.seasonal_rent_price = to_decimal(r["PrecoLocacaoTemporada"])
            prop.photos_checksum = r["ImagemHashComparacao"] or ""
            atualizado_em = to_datetime(r["DataAtualizacao"])
            prop.imported_at = atualizado_em
            prop.published_at = atualizado_em
            prop.title = PropertyService.build_title(
                {
                    "title": None,
                    "slug": None,
                    "reference_code": prop.reference_code,
                    "property_type": tipo,
                    "city": city,
                    "neighborhood": bairro,
                    "neighborhood_name": prop.neighborhood_name,
                    "sale_price": prop.sale_price,
                    "rent_price": prop.rent_price,
                    "seasonal_rent_price": prop.seasonal_rent_price,
                }
            )
            if novo or not prop.slug:
                prop.slug = self.slug_imovel(f"{prop.title} {prop.reference_code}")
            (novos if novo else alterados).append(prop)
            origem[prop.pk] = r
            if atualizado_em:
                prop.updated_at = atualizado_em
                datas.append(prop)

        todos = novos + alterados
        pks = [p.pk for p in todos]
        with transaction.atomic():
            if novos:
                Property.objects.bulk_create(novos, batch_size=300)
            if alterados:
                Property.objects.bulk_update(alterados, self.CAMPOS_IMOVEL, batch_size=200)
            if datas:
                # bulk_create aplica auto_now; a data real do legado volta aqui (bulk_update não passa pelo auto_now).
                Property.objects.bulk_update(datas, ["updated_at"], batch_size=500)
            if vinculados:
                Property.objects.bulk_update(vinculados, ["legacy_id"], batch_size=500)

            through = Property.features.through
            through.objects.filter(property_id__in=pks).delete()
            vinculos = []
            for prop in todos:
                r = origem[prop.pk]
                nomes = [(Feature.Scope.PROPERTY, n) for n in split_list(r["InfraEstruturaImovel"])]
                nomes += [(Feature.Scope.CONDOMINIUM, n) for n in split_list(r["InfraEstruturaCondominio"])]
                vistos = set()
                for scope, nome in nomes:
                    f = self.feature_por_nome(scope, nome)
                    if f and f.pk not in vistos:
                        vistos.add(f.pk)
                        vinculos.append(through(property_id=prop.pk, feature_id=f.pk))
            through.objects.bulk_create(vinculos, batch_size=1000, ignore_conflicts=True)

            PropertyFee.objects.filter(property_id__in=pks).delete()
            taxas = [fee for prop in todos for fee in self.montar_taxas(prop, origem[prop.pk]["Taxa"])]
            PropertyFee.objects.bulk_create(taxas, batch_size=1000)

            fotos_novas = 0 if self.skip_photos else self.sync_photos_lote(todos, origem)

        self.totais["criados"] += len(novos)
        self.totais["atualizados"] += len(alterados)
        self.totais["vinculados"] += len(vinculados)
        self.totais["pulados"] += pulados + repetidos
        self.totais["fotos"] += fotos_novas
        self.stats["properties"] = (
            f"{len(novos)} criados, {len(alterados)} atualizados, {len(vinculados)} já vindos do XML, "
            f"{pulados} pulados, {repetidos} com código repetido"
        )

    @staticmethod
    def montar_taxas(prop, taxa_json):
        try:
            itens = json.loads(taxa_json) if taxa_json else []
        except json.JSONDecodeError:
            itens = []
        taxas = []
        for t in itens:
            valor = to_decimal(t.get("TaxaValor"))
            descricao = (t.get("TaxaDescricao") or "").strip()
            if valor is None or not descricao:
                continue
            taxas.append(
                PropertyFee(
                    property_id=prop.pk,
                    description=descricao[:150],
                    amount=valor,
                    period=PropertyFee.Period.YEARLY if "iptu" in descricao.lower() else PropertyFee.Period.MONTHLY,
                    notes=(t.get("TaxaOBS") or "")[:300],
                )
            )
        return taxas

    def sync_photos_lote(self, props, origem):
        """
        Registra os links das fotos (não hospeda nem gera miniatura) e marca uma capa por imóvel

        Args:
            props: imóveis já salvos
            origem: linha do legado por pk do imóvel

        Returns:
            quantidade de fotos novas
        """
        por_imovel = {}
        for foto in PropertyPhoto.objects.filter(property_id__in=[p.pk for p in props]):
            por_imovel.setdefault(foto.property_id, {})[foto.source_url] = foto
        novas, alteradas = [], []
        for prop in props:
            try:
                itens = json.loads(origem[prop.pk]["Imagem"]) if origem[prop.pk]["Imagem"] else []
            except json.JSONDecodeError:
                itens = []
            atuais = por_imovel.get(prop.pk, {})
            lista = []
            for item in itens:
                url = (item.get("Url") or "").strip()[:500]
                if not url:
                    continue
                ordem = to_int(item.get("NoImagem"), len(lista) + 1)
                capa = to_bool(item.get("Mini"))
                foto = atuais.get(url)
                if foto is None:
                    foto = PropertyPhoto(property_id=prop.pk, source_url=url, sort_order=ordem, is_cover=capa)
                    atuais[url] = foto
                    novas.append(foto)
                elif foto.sort_order != ordem or foto.is_cover != capa:
                    foto.sort_order, foto.is_cover = ordem, capa
                    alteradas.append(foto)
                lista.append(foto)
            if lista and not any(f.is_cover for f in lista):
                primeira = min(lista, key=lambda f: f.sort_order)
                primeira.is_cover = True
                if primeira not in novas and primeira not in alteradas:
                    alteradas.append(primeira)
        PropertyPhoto.objects.bulk_create(novas, batch_size=1000)
        if alteradas:
            PropertyPhoto.objects.bulk_update(alteradas, ["sort_order", "is_cover"], batch_size=500)
        return len(novas)

