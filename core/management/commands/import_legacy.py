"""import_legacy — importa catálogos, portais e os imóveis de um anunciante do
banco PHP legado (MySQL 5.7, acessado direto via MySQLdb com ``DB_PORTAL_ANTIGO_*``) para os models
novos. Idempotente: tudo é casado por ``legacy_id``.

Uso::

    python manage.py import_legacy --client-id 5
    python manage.py import_legacy --client-id 5 --skip-photos      # sem registrar fotos/miniatura
    python manage.py import_legacy --client-id 5 --password 'Senha@123'
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
from core.services.images import download, ensure_cover_thumbnail
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
        parser.add_argument("--client-id", type=int, required=True, help="Id_Cliente no banco legado.")
        parser.add_argument("--password", help="Senha inicial do usuário do anunciante (gerada se omitida).")
        parser.add_argument("--skip-photos", action="store_true", help="Não registra as fotos nem gera a miniatura da capa.")
        parser.add_argument("--limit", type=int, default=0, help="Importa só os N primeiros imóveis (teste).")

    # ------------------------------------------------------------------ infra
    def handle(self, *args, **options):
        cfg = settings.LEGACY_DB
        if not cfg["host"]:
            raise CommandError("Banco legado não configurado: defina DB_PORTAL_ANTIGO_* no .env.")
        self.legacy = None
        self.conectar_legado()
        self.skip_photos = options["skip_photos"]
        self.stats = {}

        with invalidation_batch(user="import_legacy"):
            self.import_states()
            self.import_cities()
            self.import_neighborhoods()
            self.import_property_types()
            self.import_features()
            self.import_plans()
            self.import_integrators()
            self.import_portals()
            advertiser, senha = self.import_advertiser(options["client_id"], options["password"])
            self.import_properties(advertiser, options["limit"])

        self.stdout.write(self.style.SUCCESS("\nResumo:"))
        for nome, valor in self.stats.items():
            self.stdout.write(f"  {nome}: {valor}")
        if senha:
            self.stdout.write(
                self.style.WARNING(
                    f"\nUsuário do anunciante: {advertiser.email}  senha inicial: {senha}  (gravada no padrão MD5-upper do front)"
                )
            )

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
        feature = Feature.objects.filter(scope=scope, name__iexact=nome.strip()).first()
        if feature is None and create:
            feature = self.criar_feature(scope, nome.strip())
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
    def import_advertiser(self, client_id, password):
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
                if user is None:
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

            for c in self.rows("SELECT Id_Cidade FROM clientecidadeportal WHERE Id_Cliente = %s", [client_id]):
                city = City.objects.filter(legacy_id=c["Id_Cidade"]).first()
                if city:
                    AdvertiserCity.objects.get_or_create(advertiser=advertiser, city=city)

        if r["Logo"] and not advertiser.logo:
            conteudo = download(f"{LEGACY_FILES_BASE}LogoClientes/{r['Logo']}")
            if conteudo:
                advertiser.logo.save(f"{advertiser.slug}-{r['Logo']}", ContentFile(conteudo), save=True)
            else:
                self.log(self.style.WARNING("Logo não baixado."))

        self.stats["advertiser"] = f"{advertiser.name} ({advertiser.email})"
        return advertiser, senha_gerada

    # ---------------------------------------------------------------- imóveis
    def import_properties(self, advertiser, limit):
        sql = "SELECT * FROM imovel WHERE Id_Cliente = %s ORDER BY Id_Imovel"
        if limit:
            sql += f" LIMIT {int(limit)}"
        linhas = self.rows(sql, [advertiser.legacy_id])
        tipos = {t.legacy_id: t for t in PropertyType.objects.exclude(legacy_id=None)}
        cidades = {c.legacy_id: c for c in City.objects.exclude(legacy_id=None)}
        bairros = {b.legacy_id: b for b in Neighborhood.objects.exclude(legacy_id=None)}
        criados = atualizados = fotos_ok = fotos_erro = 0

        for r in linhas:
            tipo = tipos.get(to_int(r["Id_ImovelTipo"])) or tipos.get(20)
            city = cidades.get(to_int(r["Id_Cidade"]))
            if tipo is None or city is None:
                self.log(self.style.WARNING(f"Imóvel {r['Id_Imovel']} pulado: tipo/cidade sem catálogo."))
                continue
            bairro = bairros.get(to_int(r["Id_Bairro"]))
            prop = Property.objects.filter(legacy_id=r["Id_Imovel"]).first()
            novo = prop is None
            if novo:
                prop = Property(legacy_id=r["Id_Imovel"], advertiser=advertiser)

            prop.reference_code = (r["ApelidoImovel"] or str(r["Id_Imovel"])).strip()[:45]
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

            merged = {
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
            prop.title = PropertyService.build_title(merged)
            if novo or not prop.slug:
                prop.slug = unique_slug(Property, f"{prop.title} {prop.reference_code}", max_length=220, exclude_pk=prop.pk)

            with transaction.atomic():
                prop.save()
                features = [self.feature_por_nome(Feature.Scope.PROPERTY, n) for n in split_list(r["InfraEstruturaImovel"])]
                features += [self.feature_por_nome(Feature.Scope.CONDOMINIUM, n) for n in split_list(r["InfraEstruturaCondominio"])]
                prop.features.set([f for f in features if f])
                self.sync_fees(prop, r["Taxa"])
            if atualizado_em:
                Property.objects.filter(pk=prop.pk).update(updated_at=atualizado_em)

            if not self.skip_photos:
                ok, erro = self.sync_photos(prop, r["Imagem"])
                fotos_ok += ok
                fotos_erro += erro

            criados += novo
            atualizados += not novo
            self.log(f"  imóvel {prop.reference_code}: {'criado' if novo else 'atualizado'}")

        self.stats["properties"] = f"{criados} criados, {atualizados} atualizados"
        if not self.skip_photos:
            self.stats["photos"] = f"{fotos_ok} links registrados, {fotos_erro} capas sem miniatura"

    def sync_fees(self, prop, taxa_json):
        try:
            taxas = json.loads(taxa_json) if taxa_json else []
        except json.JSONDecodeError:
            taxas = []
        prop.fees.all().delete()
        for t in taxas:
            valor = to_decimal(t.get("TaxaValor"))
            descricao = (t.get("TaxaDescricao") or "").strip()
            if valor is None or not descricao:
                continue
            PropertyFee.objects.create(
                property=prop,
                description=descricao[:150],
                amount=valor,
                period=PropertyFee.Period.YEARLY if "iptu" in descricao.lower() else PropertyFee.Period.MONTHLY,
                notes=(t.get("TaxaOBS") or "")[:300],
            )

    def sync_photos(self, prop, imagem_json):
        """Fotos de XML não são hospedadas: grava só a URL externa e gera miniatura apenas da capa."""
        try:
            itens = json.loads(imagem_json) if imagem_json else []
        except json.JSONDecodeError:
            itens = []
        existentes = {p.source_url: p for p in prop.photos.all()}
        criadas = 0
        for item in itens:
            url = (item.get("Url") or "").strip()
            if not url:
                continue
            ordem = to_int(item.get("NoImagem"), len(existentes) + 1)
            capa = to_bool(item.get("Mini"))
            foto = existentes.get(url)
            if foto is None:
                foto = PropertyPhoto.objects.create(property=prop, source_url=url[:500], sort_order=ordem, is_cover=capa)
                existentes[url] = foto
                criadas += 1
            elif foto.sort_order != ordem or foto.is_cover != capa:
                foto.sort_order, foto.is_cover = ordem, capa
                foto.save(update_fields=["sort_order", "is_cover", "updated_at"])

        fotos = list(prop.photos.order_by("sort_order", "created_at"))
        if not fotos:
            return 0, 0
        capa = next((f for f in fotos if f.is_cover), fotos[0])
        if not capa.is_cover:
            capa.is_cover = True
            capa.save(update_fields=["is_cover", "updated_at"])
        ok = ensure_cover_thumbnail(capa)
        return criadas, 0 if ok else 1
