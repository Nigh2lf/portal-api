"""Models concretos do app ``core`` (domínio).

Bases abstratas (``AbstractModel``, ``SoftDeleteMixin``) e tabelas internas
de auditoria (``LogRequest``, ``LogModelChange``) ficam em
[core/models_base.py](models_base.py) — re-exportadas aqui por compatibilidade
(``from core.models import AbstractModel`` continua valendo).

Organização do arquivo:

1. **Identidade** — ``User`` + ``UserManager``
2. **RBAC** — ``Profile``, ``UserProfile``, ``Menu``, ``Permission``,
   ``ProfilePermission``
3. **Conteúdo público** — ``PublicAsset``
4. **Domínio dos portais** — seções por contexto (portal, localização,
   anunciante, imóvel, leads, publicidade, estatísticas, integração,
   conteúdo). Mapeamento legado → novo em ``docs/data-model.md``.
"""

from __future__ import annotations

import builtins
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Re-export das bases e models de infraestrutura (auditoria) para preservar
# imports legados (``from core.models import LogRequest``, etc.).
from core.models_base import (
    AbstractModel,
    LogModelChange,
    LogRequest,
    SoftDeleteManager,
    SoftDeleteMixin,
    SoftDeleteQuerySet,
)

__all__ = [
    "AbstractModel",
    "SoftDeleteManager",
    "SoftDeleteMixin",
    "SoftDeleteQuerySet",
    "LogRequest",
    "LogModelChange",
    "User",
    "UserManager",
    "Profile",
    "UserProfile",
    "Menu",
    "Permission",
    "ProfilePermission",
    "PublicAsset",
    "PostalCode",
    "LegacyIdMixin",
    "Portal",
    "PortalCity",
    "PortalMenuItem",
    "Banner",
    "State",
    "City",
    "Neighborhood",
    "Plan",
    "Integrator",
    "Advertiser",
    "AdvertiserCity",
    "AdvertiserIntegration",
    "PropertyType",
    "Feature",
    "Property",
    "PropertyPhoto",
    "PropertyFee",
    "PropertyInquiry",
    "ContactMessage",
    "PropertyRequest",
    "AdvertiserLead",
    "BlockedSender",
    "AdPlacement",
    "Ad",
    "AdImpression",
    "AdClick",
    "AdImpressionMonthly",
    "PropertyView",
    "PropertyContactClick",
    "PropertyViewMonthly",
    "SearchLog",
    "XmlImportRun",
    "XmlImportError",
    "XmlFetchLog",
    "RejectedProperty",
    "ScheduledTaskRun",
    "IntegrationLog",
    "Tip",
    "BlogPost",
]


# =============================================================================
# 1. Identidade
# =============================================================================


class UserManager(BaseUserManager):
    def _normalize(self, email):
        return self.normalize_email((email or "").strip().lower())

    def create_user(self, email, password=None):
        email = self._normalize(email)
        if not email:
            raise ValueError(_("Users must have an email"))

        user = self.model(
            email=email,
            is_active=True,
            role=User.Role.USER,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(
            email,
            password=password,
        )

        user.is_staff = True
        user.role = User.Role.ADMIN
        user.save(using=self._db)

        return user


class User(AbstractBaseUser):
    """
    Modelo de usuário.

    Dois eixos independentes (não confundir!):

    * ``is_staff``  -> acesso ao Django Admin (``/admin/``). Não tem nada a ver
      com a API. Marque ``True`` apenas para quem precisa entrar no painel
      administrativo do Django.

    * ``role``      -> papel de negócio dentro da API (ver :class:`User.Role`).
      Define o que o usuário pode fazer nas rotas REST. É o que as classes
      ``IsAdminRole`` / ``IsUserRole`` (em ``core.classes.permission_role``) e
      ``CustomPermissionClass`` checam.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        USER = "USER", "User"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile_image = models.ImageField(upload_to="profile_images", null=True, blank=True)
    email = models.EmailField(max_length=255, null=False, blank=False, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001 - opcional desde o initial; manter NULL evita migration disruptiva
    is_staff = models.BooleanField(
        default=False,
        help_text="Designa se o usuário pode acessar o Django Admin (/admin/).",
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="deleted_users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        help_text="Papel de negócio na API. Define permissões das rotas REST.",
    )
    forgot_password_hash = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001 - distinção entre 'sem token' (NULL) e 'token vazio' é semântica
    forgot_password_expire = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(
        default=False,
        help_text="Marcado como True após o usuário confirmar o código enviado por e-mail.",
    )
    email_verification_code = models.CharField(  # noqa: DJ001 - NULL = sem código pendente
        max_length=12, null=True, blank=True
    )
    email_verification_expire = models.DateTimeField(null=True, blank=True)
    profiles = models.ManyToManyField("Profile", through="UserProfile", related_name="users")

    objects = UserManager()

    USERNAME_FIELD = "email"

    def get_short_name(self):
        return self.email

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        # Acesso a ações do Django Admin: usa o eixo /admin/.
        return bool(self.is_staff)

    def has_module_perms(self, app_label):
        return bool(self.is_staff)

    @property
    def is_admin_role(self):
        """Atalho de leitura: o usuário tem papel de negócio ADMIN?"""
        return self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        # Sempre que a senha for trocada (admin, fluxo logado, reset, etc.)
        # invalida qualquer token de "esqueci minha senha" pendente.
        super().set_password(raw_password)
        self.forgot_password_hash = None
        self.forgot_password_expire = None

    # ----------------- Verificação de e-mail -----------------
    def generate_email_verification_code(self) -> str:
        """Gera novo código de 6 dígitos e atualiza expiração (não salva)."""
        import secrets as _secrets
        from datetime import timedelta as _td

        from django.conf import settings as _settings

        code = f"{_secrets.randbelow(1_000_000):06d}"
        ttl = int(getattr(_settings, "EMAIL_VERIFICATION_CODE_TTL_MIN", 30))
        self.email_verification_code = code
        self.email_verification_expire = timezone.now() + _td(minutes=ttl)
        return code

    def confirm_email_verification(self, code: str) -> bool:
        """Confirma um código. Em sucesso, marca verificado e limpa campos."""
        import secrets as _secrets

        stored = self.email_verification_code or ""
        if not stored or not _secrets.compare_digest(stored, code or ""):
            return False
        if not self.email_verification_expire or self.email_verification_expire < timezone.now():
            return False
        self.email_verified = True
        self.email_verification_code = None
        self.email_verification_expire = None
        self.save(
            update_fields=[
                "email_verified",
                "email_verification_code",
                "email_verification_expire",
            ]
        )
        return True

    def delete(self, deleted_by=None, *args, **kwargs):
        self.is_active = False
        self.deleted_at = timezone.now()
        if deleted_by is not None:
            self.deleted_by = deleted_by
        self.save(update_fields=["is_active", "deleted_at", "deleted_by"])


# =============================================================================
# 2. RBAC — Profile / Menu / Permission
# =============================================================================


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    permissions = models.ManyToManyField(
        "Permission", through="ProfilePermission", related_name="profiles"
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_profiles")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_users")

    class Meta:
        unique_together = ("user", "profile")

    def __str__(self):
        return f"{self.user_id} -> {self.profile_id}"


class Menu(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    view = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001 - opcional para menus que não mapeiam view´set
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Permission(models.Model):
    TYPE_PERMISSION = (
        ("READ", "READ"),
        ("CREATE", "CREATE"),
        ("UPDATE", "UPDATE"),
        ("DELETE", "DELETE"),
        ("OPTIONS", "OPTIONS"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="permissions_set")
    name = models.CharField(max_length=255, null=False, blank=False)
    type = models.CharField(max_length=10, choices=TYPE_PERMISSION, default="READ")
    slug = models.CharField(max_length=10, null=True, blank=True, unique=True)

    class Meta:
        unique_together = ("menu", "type")
        ordering = ("menu", "type")

    def __str__(self):
        return f"{self.menu.name}:{self.type}"


class ProfilePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="profile_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="permission_profiles"
    )

    class Meta:
        unique_together = ("profile", "permission")

    def __str__(self):
        return f"{self.profile_id} -> {self.permission_id}"


# =============================================================================
# 3. Conteúdo público
# =============================================================================


class PublicAsset(AbstractModel):
    """Imagem/arquivo público (landing page, banners, logos etc.).

    Diferente de ``User.profile_image`` (que é user-bound e pode ser privado),
    qualquer ``PublicAsset`` recebe URL pública do storage configurado.
    Em S3, o acesso público vem da bucket policy (prefixo ``public/``); o
    storage não envia ACL (bucket com ACLs desabilitadas).
    """

    name = models.CharField(max_length=120, unique=True)
    image = models.ImageField(upload_to="public/")
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_assets"
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Resolve storage no save: usa PublicMediaStorage quando AWS estiver setado.
        from django.conf import settings as _settings
        from django.core.files.storage import default_storage

        if getattr(_settings, "AWS_STORAGE_BUCKET_NAME", None):
            from config.storage import PublicMediaStorage

            self.image.storage = PublicMediaStorage()
        else:
            self.image.storage = default_storage
        super().save(*args, **kwargs)


# =============================================================================
# 4. Domínio — bases e choices
# =============================================================================


class LegacyIdMixin(models.Model):
    """Guarda a PK inteira do banco legado para migração de dados e redirects 301."""

    legacy_id = models.PositiveIntegerField(null=True, blank=True, editable=False, db_index=True)

    class Meta:
        abstract = True


class Purpose(models.TextChoices):
    SALE = "SALE", "Venda"
    RENT = "RENT", "Locação"
    SEASONAL = "SEASONAL", "Temporada"


class ContactChannel(models.TextChoices):
    PHONE = "PHONE", "Telefone"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    EMAIL = "EMAIL", "E-mail"


# =============================================================================
# 5. Domínio — localização
# =============================================================================


class State(AbstractModel):
    """Legado: ``UF``."""

    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=60)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("code",)

    def __str__(self):
        return self.code


class City(LegacyIdMixin, AbstractModel):
    """Legado: ``cidade``. ``import_aliases`` substitui a coluna ``Regras`` (nomes aceitos na importação XML)."""

    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    import_aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("name",)
        unique_together = ("state", "slug")

    def __str__(self):
        return f"{self.name}/{self.state_id and self.state.code}"


class Neighborhood(LegacyIdMixin, AbstractModel):
    """Legado: ``bairro`` (``bairro_Antigo`` descartado)."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="neighborhoods")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    import_aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("name",)
        unique_together = ("city", "slug")

    def __str__(self):
        return self.name


# =============================================================================
# 6. Domínio — portal
# =============================================================================


class Portal(LegacyIdMixin, AbstractModel):
    """Legado: ``Portal`` + ``Global.php`` de cada cidade.

    Segredos (SMTP, reCAPTCHA secret) ficam em env, não aqui.
    """

    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=120, unique=True)
    extra_domains = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    main_city = models.ForeignKey("core.City", on_delete=models.PROTECT, related_name="portals_as_main")
    cities = models.ManyToManyField("core.City", through="core.PortalCity", related_name="portals")
    combined_portals = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="aggregated_by")
    show_city_filter = models.BooleanField(default=False)

    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=300, blank=True, default="")

    seo_title = models.CharField(max_length=200)
    seo_description = models.CharField(max_length=320)
    seo_keywords = models.TextField(blank=True, default="")
    about_text = models.TextField(blank=True, default="")

    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    ga4_measurement_id = models.CharField(max_length=30, blank=True, default="")
    recaptcha_site_key = models.CharField(max_length=80, blank=True, default="")

    logo = models.ImageField(upload_to="portals/", blank=True, null=True)
    logo_mobile = models.ImageField(upload_to="portals/", blank=True, null=True)
    og_image = models.ImageField(upload_to="portals/", blank=True, null=True)
    watermark = models.ImageField(upload_to="portals/", blank=True, null=True)
    primary_color = models.CharField(max_length=9, blank=True, default="")
    secondary_color = models.CharField(max_length=9, blank=True, default="")

    realtors_page_slug = models.SlugField(max_length=80, default="imobiliarias")
    results_per_page = models.PositiveSmallIntegerField(default=30)
    thumbnail_max_width = models.PositiveSmallIntegerField(default=360)
    thumbnail_max_height = models.PositiveSmallIntegerField(default=230)
    watermark_position = models.PositiveSmallIntegerField(default=9)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("name",)

    def __str__(self):
        return self.name


class PortalCity(AbstractModel):
    """Cidades cobertas por um portal (legado: ``Portal.Cidades`` em CSV)."""

    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="portal_cities")
    city = models.ForeignKey("core.City", on_delete=models.CASCADE, related_name="city_portals")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("sort_order",)
        unique_together = ("portal", "city")

    def __str__(self):
        return f"{self.portal_id} -> {self.city_id}"


class PortalMenuItem(AbstractModel):
    """Menu principal do site (legado: ``G_Menu`` em JSON no ``Global.php``)."""

    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="menu_items")
    label = models.CharField(max_length=60)
    path = models.CharField(max_length=200)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("portal", "sort_order")

    def __str__(self):
        return f"{self.portal_id}: {self.label}"


class Banner(AbstractModel):
    """Legado: ``banner``. Imagens de fundo do hero da home e do topo das internas."""

    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="banners", null=True, blank=True)
    home_image = models.ImageField(upload_to="banners/")
    inner_image = models.ImageField(upload_to="banners/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return str(self.home_image)


# =============================================================================
# 7. Domínio — anunciante e plano
# =============================================================================


class Plan(LegacyIdMixin, AbstractModel):
    """Legado: ``Produto``. ``monthly_price`` nulo = "sob consulta"."""

    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=60, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    property_limit = models.PositiveIntegerField()
    photo_limit = models.PositiveIntegerField()
    featured_limit = models.PositiveIntegerField(default=0)
    has_realtor_page = models.BooleanField(default=False)
    receives_property_requests = models.BooleanField(default=False)
    has_hotsite = models.BooleanField(default=False)
    is_owner_only = models.BooleanField(default=False)
    is_recommended = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Integrator(LegacyIdMixin, AbstractModel):
    """Legado: ``Integrador`` (Vista, VivaReal, Union, ValueGaia...)."""

    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Advertiser(LegacyIdMixin, SoftDeleteMixin, AbstractModel):
    """Legado: ``cliente``. Quem anuncia: proprietário, corretor ou imobiliária.

    O login fica em ``core.User`` (``user``); ``legacy_password_md5`` só existe
    para validar a senha antiga no primeiro acesso e então ser apagada.
    Limites ``*_limit`` são overrides; nulo = usa o do plano.
    """

    class Type(models.TextChoices):
        OWNER = "OWNER", "Proprietário"
        BROKER = "BROKER", "Corretor"
        AGENCY = "AGENCY", "Imobiliária"

    user = models.OneToOneField("core.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="advertiser_profile")
    portal = models.ForeignKey("core.Portal", on_delete=models.PROTECT, related_name="advertisers")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="advertisers")
    type = models.CharField(max_length=10, choices=Type.choices)

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    document = models.CharField(max_length=14, blank=True, default="")
    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    phone_secondary = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    website = models.URLField(max_length=200, blank=True, default="")
    address = models.CharField(max_length=300, blank=True, default="")
    logo = models.ImageField(upload_to="advertisers/", blank=True, null=True)
    creci = models.CharField(max_length=20, blank=True, default="")
    contact_name = models.CharField(max_length=80, blank=True, default="")
    responsible_broker = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    coupon = models.CharField(max_length=45, blank=True, default="")

    is_published = models.BooleanField(default=False, help_text="Aparece no portal (legado: cliente.Portal).")
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    notify_by_email = models.BooleanField(default=True)
    has_hotsite = models.BooleanField(default=False)
    has_realtor_page = models.BooleanField(default=False)
    receives_property_requests = models.BooleanField(default=False)
    property_limit = models.PositiveIntegerField(null=True, blank=True)
    photo_limit = models.PositiveIntegerField(null=True, blank=True)
    featured_limit = models.PositiveIntegerField(null=True, blank=True)
    super_featured_limit = models.PositiveIntegerField(null=True, blank=True)

    legacy_password_md5 = models.CharField(max_length=32, blank=True, default="", editable=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("name",)
        indexes = [models.Index(fields=["portal", "is_published"])]

    def __str__(self):
        return self.name

    @property
    def effective_property_limit(self):
        return self.property_limit if self.property_limit is not None else self.plan.property_limit

    @property
    def effective_photo_limit(self):
        return self.photo_limit if self.photo_limit is not None else self.plan.photo_limit

    @property
    def effective_featured_limit(self):
        return self.featured_limit if self.featured_limit is not None else self.plan.featured_limit


class AdvertiserCity(AbstractModel):
    """Legado: ``clientecidadeportal``. Cidades em que o anunciante atua."""

    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE, related_name="advertiser_cities")
    city = models.ForeignKey("core.City", on_delete=models.CASCADE, related_name="city_advertisers")

    class Meta(AbstractModel.Meta):
        app_label = "core"
        unique_together = ("advertiser", "city")

    def __str__(self):
        return f"{self.advertiser_id} -> {self.city_id}"


class AdvertiserIntegration(AbstractModel):
    """Legado: colunas de integração espalhadas em ``cliente`` (URL_XML, TokenGaia, Vista_*)."""

    advertiser = models.OneToOneField(Advertiser, on_delete=models.CASCADE, related_name="integration")
    integrator = models.ForeignKey(Integrator, on_delete=models.SET_NULL, null=True, blank=True, related_name="advertisers")
    xml_url = models.URLField(max_length=300, blank=True, default="")
    xml_default_url = models.URLField(max_length=300, blank=True, default="")
    api_token = models.CharField(max_length=100, blank=True, default="")
    vista_portal_key = models.CharField(max_length=100, blank=True, default="")
    vista_customer_code = models.CharField(max_length=100, blank=True, default="")
    vista_customer_key = models.CharField(max_length=50, blank=True, default="")
    vista_api_url = models.URLField(max_length=200, blank=True, default="")
    save_all_images = models.BooleanField(default=False)
    skip_thumbnails = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_imported_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"integração de {self.advertiser_id}"


# =============================================================================
# 8. Domínio — imóvel
# =============================================================================


class PropertyType(LegacyIdMixin, AbstractModel):
    """Legado: ``imoveltipo``."""

    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=60, unique=True)
    import_aliases = models.JSONField(default=list, blank=True)
    mercadolivre_category = models.CharField(max_length=70, blank=True, default="")
    is_residential = models.BooleanField(default=True, help_text="Mostra quartos/suítes/banheiros no cadastro.")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Feature(LegacyIdMixin, AbstractModel):
    """Legado: ``imovelinfra`` (escopo PROPERTY) e ``imovelinfracondominio`` (escopo CONDOMINIUM)."""

    class Scope(models.TextChoices):
        PROPERTY = "PROPERTY", "Imóvel"
        CONDOMINIUM = "CONDOMINIUM", "Condomínio"

    scope = models.CharField(max_length=12, choices=Scope.choices)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("scope", "sort_order", "name")
        unique_together = ("scope", "slug")

    def __str__(self):
        return f"{self.get_scope_display()}: {self.name}"


class Property(LegacyIdMixin, SoftDeleteMixin, AbstractModel):
    """Legado: ``imovel`` (+ view ``imovelportal``).

    Objetivo (venda/locação/temporada) é derivado dos preços preenchidos, como
    no legado. Portal vem do anunciante. ``neighborhood_name`` cobre o "outro
    bairro" (legado: ``Id_Bairro = 417`` + texto livre).
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        PUBLISHED = "PUBLISHED", "Publicado"

    class AdType(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        FEATURED = "FEATURED", "Destaque"
        SUPER_FEATURED = "SUPER_FEATURED", "Superdestaque"

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="properties")
    reference_code = models.CharField(max_length=45)
    slug = models.SlugField(max_length=220, unique=True)
    title = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED)
    is_active = models.BooleanField(default=True)
    ad_type = models.CharField(max_length=16, choices=AdType.choices, default=AdType.NORMAL, db_index=True, help_text="Legado: Destaque 0/1/2.")

    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT, related_name="properties")
    city = models.ForeignKey("core.City", on_delete=models.PROTECT, related_name="properties")
    neighborhood = models.ForeignKey("core.Neighborhood", on_delete=models.SET_NULL, null=True, blank=True, related_name="properties")
    neighborhood_name = models.CharField(max_length=120, blank=True, default="")
    is_in_condominium = models.BooleanField(default=False)

    bedrooms = models.PositiveSmallIntegerField(default=0)
    suites = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    parking_spaces = models.PositiveSmallIntegerField(default=0)
    built_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, default="")

    sale_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rent_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    seasonal_rent_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    features = models.ManyToManyField(Feature, blank=True, related_name="properties")

    photos_checksum = models.CharField(max_length=32, blank=True, default="", editable=False)
    imported_at = models.DateTimeField(null=True, blank=True, help_text="Última atualização vinda do XML.")
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        verbose_name_plural = "properties"
        ordering = ("-updated_at",)
        unique_together = ("advertiser", "reference_code")
        indexes = [
            models.Index(fields=["is_active", "status"]),
            models.Index(fields=["city", "neighborhood"]),
            models.Index(fields=["property_type"]),
            models.Index(fields=["sale_price"]),
            models.Index(fields=["rent_price"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"{self.reference_code} - {self.title}"

    @builtins.property
    def is_featured(self):
        """Destaque ou superdestaque (conta no limite de destaques do plano)."""
        return self.ad_type != self.AdType.NORMAL

    @staticmethod
    def ad_rank_expression():
        """Expressão para ordenar superdestaque > destaque > normal em querysets."""
        from django.db.models import Case, IntegerField, Value, When

        return Case(
            When(ad_type="SUPER_FEATURED", then=Value(2)),
            When(ad_type="FEATURED", then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )


def property_photo_path(instance, filename):
    """``properties/<slug-do-imovel>-<uid>.<ext>``."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "jpg").lower()[:5]
    return f"properties/{instance.property.slug}-{uuid.uuid4().hex[:10]}.{ext}"


def property_thumbnail_path(instance, filename):
    """``properties/thumbs/<slug-do-imovel>-<uid>.jpg``."""
    return f"properties/thumbs/{instance.property.slug}-{uuid.uuid4().hex[:10]}.jpg"


class PropertyPhoto(LegacyIdMixin, AbstractModel):
    """Legado: ``imovelfoto`` + JSON em ``imovel.Imagem``. Uma linha por foto; ``is_cover`` = miniatura principal.

    Fotos de imóveis integrados por XML não são hospedadas: ficam só em
    ``source_url`` (``image`` vazio) e apenas a capa ganha ``thumbnail``. Fotos
    enviadas pelo painel do portal são gravadas em ``image``.
    """

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=property_photo_path, blank=True, null=True)
    thumbnail = models.ImageField(upload_to=property_thumbnail_path, blank=True, null=True)
    source_url = models.URLField(max_length=500, blank=True, default="", help_text="URL original quando veio do XML.")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.property_id} #{self.sort_order}"

    @builtins.property
    def is_hosted(self):
        return bool(self.image)

    @builtins.property
    def display_url(self):
        """URL da foto em tamanho cheio: hospedada ou a externa do anunciante."""
        if self.image:
            return self.image.url
        return self.source_url or None


class PropertyFee(LegacyIdMixin, AbstractModel):
    """Legado: ``imoveltaxa`` (IPTU, condomínio...)."""

    class Period(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensal"
        YEARLY = "YEARLY", "Anual"
        ONE_TIME = "ONE_TIME", "Única"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="fees")
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.CharField(max_length=10, choices=Period.choices, default=Period.MONTHLY)
    notes = models.CharField(max_length=300, blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"{self.description}: {self.amount}"


# =============================================================================
# 9. Domínio — leads e contatos
# =============================================================================


class PropertyInquiry(LegacyIdMixin, AbstractModel):
    """Legado: ``mensagem``. Lead de um visitante sobre um imóvel ("Fale com o anunciante")."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="inquiries")
    property = models.ForeignKey("core.Property", on_delete=models.SET_NULL, null=True, blank=True, related_name="inquiries")
    property_reference_code = models.CharField(max_length=45, blank=True, default="")
    portal = models.ForeignKey("core.Portal", on_delete=models.PROTECT, related_name="inquiries")
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    message = models.TextField()
    contact_preferences = models.JSONField(default=list, blank=True, help_text='Ex.: ["WHATSAPP", "EMAIL"]')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referer = models.TextField(blank=True, default="")
    is_mobile = models.BooleanField(default=False)
    forwarded_to_crm_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        verbose_name_plural = "property inquiries"
        indexes = [models.Index(fields=["advertiser", "-created_at"])]

    def __str__(self):
        return f"{self.name} -> {self.property_reference_code}"


class ContactMessage(LegacyIdMixin, AbstractModel):
    """Legado: ``Contato`` (só a parte "fale conosco"; a encomenda virou ``PropertyRequest``)."""

    portal = models.ForeignKey("core.Portal", on_delete=models.PROTECT, related_name="contact_messages")
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    subject = models.CharField(max_length=100, blank=True, default="")
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"{self.name}: {self.subject}"


class PropertyRequest(LegacyIdMixin, AbstractModel):
    """Legado: ``EncomendaImovel`` + campos de encomenda em ``Contato``.

    ``is_partner_broadcast`` = versão "parceiro", enviada aos anunciantes com
    ``receives_property_requests``.
    """

    class Funding(models.TextChoices):
        FINANCING = "FINANCING", "Financiamento"
        CASH = "CASH", "À vista"
        FGTS = "FGTS", "FGTS"
        EXCHANGE = "EXCHANGE", "Permuta"

    portal = models.ForeignKey("core.Portal", on_delete=models.PROTECT, related_name="property_requests")
    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.SET_NULL, null=True, blank=True, related_name="property_requests")
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    purpose = models.CharField(max_length=10, choices=Purpose.choices, default=Purpose.SALE)
    property_type = models.ForeignKey("core.PropertyType", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey("core.City", on_delete=models.SET_NULL, null=True, blank=True)
    neighborhood = models.ForeignKey("core.Neighborhood", on_delete=models.SET_NULL, null=True, blank=True)
    min_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_in_condominium = models.BooleanField(null=True, blank=True)
    funding = models.CharField(max_length=10, choices=Funding.choices, blank=True, default="")
    message = models.TextField(blank=True, default="")
    is_partner_broadcast = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"{self.name} ({self.get_purpose_display()})"


class AdvertiserLead(LegacyIdMixin, AbstractModel):
    """Legado: ``LeadSite``. Interessado em anunciar (landing B2B / página Anunciar)."""

    portal = models.ForeignKey("core.Portal", on_delete=models.PROTECT, related_name="advertiser_leads")
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    company = models.CharField(max_length=120, blank=True, default="")
    message = models.TextField(blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return self.name


class BlockedSender(LegacyIdMixin, AbstractModel):
    """Legado: ``BloqueioRemetente`` + ``BloqueioAcesso``. Antispam por e-mail e/ou IP."""

    email = models.EmailField(max_length=120, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return self.email or str(self.ip_address)


# =============================================================================
# 10. Domínio — publicidade
# =============================================================================


class AdPlacement(LegacyIdMixin, AbstractModel):
    """Legado: ``PublicidadeCategoria`` + tabela de preços de ``Publicidade.php``."""

    class Page(models.TextChoices):
        HOME = "HOME", "Home"
        SEARCH = "SEARCH", "Lista de imóveis"
        PROPERTY = "PROPERTY", "Detalhe do imóvel"

    class Kind(models.TextChoices):
        POPUP = "POPUP", "Pop-up"
        HORIZONTAL = "HORIZONTAL", "Banner horizontal"
        SIDEBAR = "SIDEBAR", "Banner lateral"

    code = models.CharField(max_length=10, unique=True, help_text="Ex.: PH1, BH1, BL1")
    name = models.CharField(max_length=60)
    page = models.CharField(max_length=10, choices=Page.choices)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    width = models.PositiveSmallIntegerField()
    height = models.PositiveSmallIntegerField()
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Ad(LegacyIdMixin, AbstractModel):
    """Legado: ``Publicidade``."""

    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, related_name="ads")
    placement = models.ForeignKey(AdPlacement, on_delete=models.PROTECT, related_name="ads")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="ads/")
    link_url = models.URLField(max_length=300, blank=True, default="")
    open_in_new_tab = models.BooleanField(default=False)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [models.Index(fields=["portal", "placement", "is_active"])]

    def __str__(self):
        return self.name


class AdImpression(AbstractModel):
    """Legado: ``PublicidadeAcesso``."""

    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="impressions")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referer = models.TextField(blank=True, default="")
    is_mobile = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [models.Index(fields=["ad", "-created_at"])]

    def __str__(self):
        return f"{self.ad_id} @ {self.created_at}"


class AdClick(AbstractModel):
    """Legado: ``PublicidadeClick``."""

    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referer = models.TextField(blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [models.Index(fields=["ad", "-created_at"])]

    def __str__(self):
        return f"{self.ad_id} @ {self.created_at}"


class AdImpressionMonthly(AbstractModel):
    """Legado: ``PublicidadeAcessoAgrupada``. Condensação mensal feita por cron."""

    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="monthly_impressions")
    year_month = models.CharField(max_length=7, help_text="AAAA-MM")
    total_impressions = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        unique_together = ("ad", "year_month")

    def __str__(self):
        return f"{self.ad_id} {self.year_month}"


# =============================================================================
# 11. Domínio — estatísticas
# =============================================================================


class PropertyView(AbstractModel):
    """Legado: ``EstatisticaImovelAcesso``. Uma linha por visualização do detalhe."""

    property = models.ForeignKey("core.Property", on_delete=models.SET_NULL, null=True, blank=True, related_name="views")
    property_reference_code = models.CharField(max_length=45, blank=True, default="")
    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="property_views")
    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, related_name="property_views")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referer = models.TextField(blank=True, default="")
    is_mobile = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [
            models.Index(fields=["advertiser", "-created_at"]),
            models.Index(fields=["property", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.property_reference_code} @ {self.created_at}"


class PropertyContactClick(AbstractModel):
    """Legado: ``EstatisticaImovelClick``. Clique em "ver telefone" ou WhatsApp."""

    property = models.ForeignKey("core.Property", on_delete=models.SET_NULL, null=True, blank=True, related_name="contact_clicks")
    property_reference_code = models.CharField(max_length=45, blank=True, default="")
    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="contact_clicks")
    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, related_name="contact_clicks")
    channel = models.CharField(max_length=10, choices=ContactChannel.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_mobile = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [models.Index(fields=["advertiser", "channel", "-created_at"])]

    def __str__(self):
        return f"{self.channel} {self.property_reference_code}"


class PropertyViewMonthly(AbstractModel):
    """Legado: ``EstatisticaImovelAcessoAgrupada``. Condensação mensal por anunciante (cron)."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="monthly_views")
    year_month = models.CharField(max_length=7, help_text="AAAA-MM")
    total_views = models.PositiveIntegerField(default=0)
    mobile_views = models.PositiveIntegerField(default=0)
    phone_clicks = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    inquiries = models.PositiveIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        unique_together = ("advertiser", "year_month")

    def __str__(self):
        return f"{self.advertiser_id} {self.year_month}"


class SearchLog(AbstractModel):
    """Legado: ``PesquisasSalvas``. Alimenta "mais procurados" e o mapa do site."""

    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, related_name="search_logs")
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    property_type = models.ForeignKey("core.PropertyType", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey("core.City", on_delete=models.SET_NULL, null=True, blank=True)
    neighborhood = models.ForeignKey("core.Neighborhood", on_delete=models.SET_NULL, null=True, blank=True)
    bedrooms = models.JSONField(default=list, blank=True)
    is_in_condominium = models.BooleanField(null=True, blank=True)
    min_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    page = models.PositiveSmallIntegerField(default=1)
    is_mobile = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        indexes = [models.Index(fields=["portal", "-created_at"])]

    def __str__(self):
        return f"{self.portal_id} {self.purpose} {self.created_at:%Y-%m-%d}"


# =============================================================================
# 12. Domínio — integração e jobs
# =============================================================================


class XmlImportRun(LegacyIdMixin, AbstractModel):
    """Legado: ``ControleImportacao``. Uma execução da importação XML de um anunciante."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="import_runs")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    total_properties = models.PositiveIntegerField(default=0)
    valid_properties = models.PositiveIntegerField(default=0)
    invalid_properties = models.PositiveIntegerField(default=0)
    report_email_sent = models.BooleanField(default=False)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.advertiser_id} @ {self.started_at:%Y-%m-%d %H:%M}"


class XmlImportError(LegacyIdMixin, AbstractModel):
    """Legado: ``ErroImportacao``."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="import_errors")
    run = models.ForeignKey(XmlImportRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="errors")
    property_reference_code = models.CharField(max_length=45, blank=True, default="")
    message = models.TextField()
    payload = models.TextField(blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"{self.property_reference_code}: {self.message[:60]}"


class XmlFetchLog(LegacyIdMixin, AbstractModel):
    """Legado: ``ControleXMLLocal`` + ``ImportacaoXML``. Download/snapshot do XML."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="xml_fetches")
    source = models.CharField(max_length=45, blank=True, default="")
    url = models.URLField(max_length=300, blank=True, default="")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    succeeded = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.advertiser_id} {self.source}"


class RejectedProperty(AbstractModel):
    """Legado: view ``imovelrejeitado``. Imóveis do XML barrados pela moderação."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.CASCADE, related_name="rejected_properties")
    property_reference_code = models.CharField(max_length=45)
    reason = models.CharField(max_length=200, blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"
        verbose_name_plural = "rejected properties"
        unique_together = ("advertiser", "property_reference_code")

    def __str__(self):
        return f"{self.advertiser_id}:{self.property_reference_code}"


class ScheduledTaskRun(LegacyIdMixin, AbstractModel):
    """Legado: ``ControleTarefasAutomaticas``. Histórico dos jobs do cron."""

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Executando"
        SUCCESS = "SUCCESS", "Sucesso"
        FAILED = "FAILED", "Falhou"

    name = models.CharField(max_length=60)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True, default="")

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.name} {self.status}"


class IntegrationLog(LegacyIdMixin, AbstractModel):
    """Legado: ``API_Retorno``. Request/response de integrações externas (CRM Vista etc.)."""

    advertiser = models.ForeignKey("core.Advertiser", on_delete=models.SET_NULL, null=True, blank=True, related_name="integration_logs")
    service = models.CharField(max_length=40, blank=True, default="")
    request_payload = models.TextField(blank=True, default="")
    response_payload = models.TextField(blank=True, default="")
    succeeded = models.BooleanField(default=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"

    def __str__(self):
        return f"{self.service} {self.created_at:%Y-%m-%d %H:%M}"


# =============================================================================
# 13. Domínio — conteúdo
# =============================================================================


class Tip(LegacyIdMixin, AbstractModel):
    """Legado: ``dica``. ``portal`` nulo = vale para todos."""

    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, null=True, blank=True, related_name="tips")
    title = models.CharField(max_length=150)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("sort_order", "-published_at")

    def __str__(self):
        return self.title


class BlogPost(LegacyIdMixin, AbstractModel):
    """Legado: WordPress ``wp_posts`` (banco ``blogportal``). ``portal`` nulo = vale para todos."""

    portal = models.ForeignKey("core.Portal", on_delete=models.CASCADE, null=True, blank=True, related_name="blog_posts")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    excerpt = models.CharField(max_length=400, blank=True, default="")
    body = models.TextField()
    author_name = models.CharField(max_length=100, blank=True, default="")
    cover_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractModel.Meta):
        app_label = "core"
        ordering = ("-published_at",)

    def __str__(self):
        return self.title

# =============================================================================
# 14. Infra — cache de CEP (ViaCEP)
# =============================================================================


class PostalCode(models.Model):
    """Resultado da ViaCEP gravado localmente; ``not_found`` evita reconsultar CEP inexistente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cep = models.CharField(max_length=8, unique=True)
    street = models.CharField(max_length=200, blank=True, default="")
    complement = models.CharField(max_length=200, blank=True, default="")
    neighborhood = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    state_code = models.CharField(max_length=2, blank=True, default="")
    ibge_code = models.CharField(max_length=10, blank=True, default="")
    raw = models.JSONField(default=dict, blank=True)
    not_found = models.BooleanField(default=False)
    fetched_at = models.DateTimeField()

    class Meta:
        app_label = "core"
        ordering = ("cep",)

    def __str__(self):
        return self.cep
