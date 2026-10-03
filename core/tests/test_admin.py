"""Auto-admin: registro automático e preservação de admins manuais."""

from __future__ import annotations

from django.apps import apps
from django.contrib import admin

from core.admin import UserAdmin
from core.models import PublicAsset, User


def test_all_core_models_registered_in_admin() -> None:
    for model in apps.get_app_config("core").get_models():
        assert admin.site.is_registered(
            model
        ), f"Modelo {model.__name__} não foi registrado no admin."


def test_manual_admin_is_preserved() -> None:
    # User tem admin manual; auto-registro NÃO deve ter sobrescrito.
    assert isinstance(admin.site._registry[User], UserAdmin)


def test_inferred_admin_has_search_fields() -> None:
    registered = admin.site._registry[PublicAsset]
    assert registered.search_fields
