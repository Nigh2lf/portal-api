from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as DjangoGroup

from core.models import (
    LogModelChange,
    LogRequest,
    Menu,
    Permission,
    Profile,
    ProfilePermission,
    PublicAsset,
    User,
    UserProfile,
)

admin.site.site_header = f"{settings.PROJECT_NAME} Admin"
admin.site.site_title = f"{settings.PROJECT_NAME} Admin"
admin.site.index_title = settings.PROJECT_NAME


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "name",
        "role",
        "is_staff",
        "is_active",
        "email_verified",
        "last_login",
        "created_at",
    )
    list_filter = ("is_staff", "is_active", "role", "email_verified", "last_login")
    search_fields = ("email", "name")
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at", "deleted_at", "deleted_by", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password", "profile_image", "name", "is_active", "role")}),
        ("Permissions", {"fields": ("is_staff",)}),
        ("Email verification", {"fields": ("email_verified",)}),
        (
            "Audit",
            {"fields": ("last_login", "created_at", "updated_at", "deleted_at", "deleted_by")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "view")
    search_fields = ("name", "view")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "menu", "name", "type")
    list_filter = ("type", "menu")
    search_fields = ("name", "menu__name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "profile")
    search_fields = ("user__email", "profile__name")


@admin.register(ProfilePermission)
class ProfilePermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "permission")
    search_fields = ("profile__name", "permission__name")


@admin.register(PublicAsset)
class PublicAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "uploaded_by", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LogRequest)
class LogRequestAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "method",
        "path",
        "status_code",
        "execution_time",
        "user_email",
        "ip",
    )
    list_filter = ("method", "status_code")
    search_fields = ("path", "ip", "user_agent", "user_email")
    readonly_fields = (
        "id",
        "timestamp",
        "method",
        "path",
        "execution_time",
        "status_code",
        "data",
        "ip",
        "params",
        "user_agent",
        "curl",
        "user",
        "user_email",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LogModelChange)
class LogModelChangeAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "app_label",
        "model_name",
        "object_id",
        "actor_email",
    )
    list_filter = ("action", "app_label", "model_name")
    search_fields = ("object_id", "actor_email", "model_name")
    readonly_fields = (
        "id",
        "app_label",
        "model_name",
        "object_id",
        "action",
        "changes",
        "actor",
        "actor_email",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.unregister(DjangoGroup)

# Auto-registra qualquer modelo do app `core` que ainda no tenha admin manual.
# Modelos novos ganham admin "de graa" com search/filter/list_display
# inferidos. Para customizar, basta declarar @admin.register(MyModel) acima
# desta linha que o auto-registro respeita.
from core.classes.auto_admin import autoregister  # noqa: E402

autoregister("core")

# ---------------------------------------------------------------------------
# MFA opcional no Django Admin (django-otp).
# Liga via env ADMIN_MFA_ENABLED=True. Apps/middleware do otp já estão
# carregados sempre (settings.py) para que as migrations existam, mas a
# exigência de TOTP/static token só acontece quando o flag está ativo.
# ---------------------------------------------------------------------------
if getattr(settings, "ADMIN_MFA_ENABLED", False):
    from django_otp.admin import OTPAdminSite

    admin.site.__class__ = OTPAdminSite
