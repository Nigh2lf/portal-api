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
"""

from __future__ import annotations

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
