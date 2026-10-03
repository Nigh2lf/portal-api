"""Auditoria de permissões + SafeDefaultPermission + CustomPermissionClass."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from rest_framework.exceptions import PermissionDenied

from core.classes.permission import CustomPermissionClass, SafeDefaultPermission

# --- Auditoria global do router ---------------------------------------------


def test_all_router_viewsets_have_explicit_permissions() -> None:
    from config.urls_v1 import router
    from core.checks import _has_explicit_permissions

    offenders = [
        vs.__name__
        for _prefix, vs, _basename in router.registry
        if not _has_explicit_permissions(vs)
    ]
    assert offenders == [], (
        f"ViewSets sem permission_classes/get_permissions: {offenders}. "
        "Toda nova ViewSet DEVE declarar permissões explicitamente."
    )


def test_custom_permission_class_requires_view_name() -> None:
    from config.urls_v1 import router
    from core.checks import _uses_custom_permission_class

    offenders = [
        vs.__name__
        for _p, vs, _b in router.registry
        if _uses_custom_permission_class(vs) and not getattr(vs, "view_name", None)
    ]
    assert offenders == [], f"ViewSets usando CustomPermissionClass sem view_name: {offenders}."


# --- SafeDefaultPermission ---------------------------------------------------


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_safe_default_allows_safe_methods(method: str) -> None:
    perm = SafeDefaultPermission()
    req = Mock(method=method)
    assert perm.has_permission(req, view=Mock()) is True


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_safe_default_blocks_destructive_methods(method: str) -> None:
    perm = SafeDefaultPermission()
    req = Mock(method=method)
    assert perm.has_permission(req, view=Mock()) is False


# --- CustomPermissionClass ---------------------------------------------------


@pytest.mark.django_db
def test_custom_permission_denies_when_view_name_missing(user) -> None:
    from core.models import User as UserModel

    user.role = UserModel.Role.USER
    user.save()
    view = Mock(spec=[])  # sem view_name
    req = Mock(user=user, method="GET")
    with pytest.raises(PermissionDenied):
        CustomPermissionClass().has_permission(req, view)


@pytest.mark.django_db
def test_router_user_blocks_role_outside_list(user) -> None:
    """`router_user` barra o papel antes mesmo de consultar as permissões."""
    view = Mock(spec=["view_name", "router_user"], view_name="x", router_user=["ADMIN"])
    req = Mock(user=user, method="GET")  # fixture `user` tem role USER
    with pytest.raises(PermissionDenied):
        CustomPermissionClass().has_permission(req, view)


def _grant_read(user, view_name: str) -> None:
    """Dá ao usuário a permissão READ do menu ``view_name``."""
    from core.models import (
        Menu,
        Permission,
        Profile,
        ProfilePermission,
        UserProfile,
    )

    menu = Menu.objects.create(name=view_name, view=view_name)
    perm = Permission.objects.create(menu=menu, name=f"Leitura de {view_name}", type="READ")
    profile = Profile.objects.create(name=f"perfil-{view_name}", is_active=True)
    ProfilePermission.objects.create(profile=profile, permission=perm)
    UserProfile.objects.create(user=user, profile=profile)


@pytest.mark.django_db
def test_router_user_allows_role_inside_list(admin_user) -> None:
    """Papel dentro de `router_user` segue o fluxo normal e passa com a perm."""
    _grant_read(admin_user, "painel")

    view = Mock(spec=["view_name", "router_user"], view_name="painel", router_user=["ADMIN"])
    req = Mock(user=admin_user, method="GET")
    assert CustomPermissionClass().has_permission(req, view) is True


@pytest.mark.django_db
def test_view_read_collapses_every_method_into_read(user) -> None:
    """Com `view_read=True`, quem tem READ também faz DELETE."""
    _grant_read(user, "painel")

    read_only_view = Mock(spec=["view_name", "view_read"], view_name="painel", view_read=True)
    req = Mock(user=user, method="DELETE")
    assert CustomPermissionClass().has_permission(req, read_only_view) is True


@pytest.mark.django_db
def test_without_view_read_delete_requires_delete_permission(user) -> None:
    _grant_read(user, "painel")

    strict_view = Mock(spec=["view_name"], view_name="painel")
    assert (
        CustomPermissionClass().has_permission(Mock(user=user, method="GET"), strict_view) is True
    )
    assert (
        CustomPermissionClass().has_permission(Mock(user=user, method="DELETE"), strict_view)
        is False
    )
