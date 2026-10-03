"""Checks de produção, AllowAny justificado, PII em serializers, migrations pendentes."""

from __future__ import annotations

from pathlib import Path

from rest_framework import serializers

from core.checks import (
    check_allow_any_justification,
    check_production_hardening,
    check_serializers_pii,
    check_unapplied_migrations,
)

# --- Production hardening ---------------------------------------------------


def test_production_hardening_no_issues_in_debug(settings) -> None:
    settings.DEBUG = True
    assert check_production_hardening(None) == []


def test_weak_secret_key_blocks_prod(settings) -> None:
    settings.DEBUG = False
    settings.SECRET_KEY = "change-me-please"
    settings.ALLOWED_HOSTS = ["api.x.com"]
    settings.CORS_ALLOW_ALL_ORIGINS = False
    settings.BREVO_API_KEY = "x"
    settings.SECURE_SSL_REDIRECT = True

    issues = check_production_hardening(None)
    assert "core.E004" in [i.id for i in issues]


def test_wildcard_allowed_hosts_blocks_prod(settings) -> None:
    settings.DEBUG = False
    settings.SECRET_KEY = "x" * 60
    settings.ALLOWED_HOSTS = ["*"]
    settings.CORS_ALLOW_ALL_ORIGINS = False
    settings.BREVO_API_KEY = "x"
    settings.SECURE_SSL_REDIRECT = True

    issues = check_production_hardening(None)
    assert "core.E005" in [i.id for i in issues]


# --- AllowAny precisa de justificativa --------------------------------------


def _run_allow_any_check(tmp_path: Path, content: str, settings):
    view_dir = tmp_path / "core" / "views"
    view_dir.mkdir(parents=True)
    (view_dir / "fake.py").write_text(content, encoding="utf-8")
    settings.BASE_DIR = str(tmp_path)
    return check_allow_any_justification(None)


def test_allow_any_without_comment_warns(tmp_path: Path, settings) -> None:
    issues = _run_allow_any_check(
        tmp_path,
        "from rest_framework.permissions import AllowAny\npermission_classes = [AllowAny]\n",
        settings,
    )
    assert any(i.id == "core.W006" for i in issues)


def test_allow_any_with_inline_comment_passes(tmp_path: Path, settings) -> None:
    issues = _run_allow_any_check(
        tmp_path,
        "from rest_framework.permissions import AllowAny\n"
        "permission_classes = [AllowAny]  # allow-any: rota publica\n",
        settings,
    )
    assert issues == []


def test_real_codebase_has_no_unjustified_allow_any() -> None:
    assert check_allow_any_justification(None) == []


# --- PII em serializers -----------------------------------------------------


def test_real_codebase_serializers_are_clean() -> None:
    issues = [i for i in check_serializers_pii(None) if "core.fake" not in i.msg]
    assert issues == []


def test_fields_all_warns() -> None:
    from core.models import Menu

    Bad = type(
        "BadAllFieldsSerializer",
        (serializers.ModelSerializer,),
        {
            "Meta": type("Meta", (), {"model": Menu, "fields": "__all__"}),
            "__module__": "core.fake",
        },
    )
    try:
        issues = check_serializers_pii(None)
        assert any(i.id == "core.W007" and "BadAllFieldsSerializer" in i.msg for i in issues)
    finally:
        del Bad


def test_pii_field_warns() -> None:
    from core.models import User

    Leaky = type(
        "LeakyPiiSerializer",
        (serializers.ModelSerializer,),
        {
            "Meta": type(
                "Meta",
                (),
                {
                    "model": User,
                    "fields": ("id", "email", "password", "forgot_password_hash"),
                },
            ),
            "__module__": "core.fake",
        },
    )
    try:
        issues = check_serializers_pii(None)
        leaks = [i for i in issues if i.id == "core.W008" and "LeakyPiiSerializer" in i.msg]
        assert leaks
        assert "forgot_password_hash" in leaks[0].msg
    finally:
        del Leaky


def test_write_only_pii_is_safe() -> None:
    from core.models import User

    Safe = type(
        "SafeWriteOnlySerializer",
        (serializers.ModelSerializer,),
        {
            "password": serializers.CharField(write_only=True),
            "Meta": type(
                "Meta",
                (),
                {"model": User, "fields": ("id", "email", "password")},
            ),
            "__module__": "core.fake",
        },
    )
    try:
        issues = check_serializers_pii(None)
        assert not any(i.id == "core.W008" and "SafeWriteOnlySerializer" in i.msg for i in issues)
    finally:
        del Safe


def test_allow_all_fields_opt_out_silences_warning() -> None:
    from core.models import Menu

    Acked = type(
        "AckedAllFieldsSerializer",
        (serializers.ModelSerializer,),
        {
            "Meta": type(
                "Meta",
                (),
                {"model": Menu, "fields": "__all__", "allow_all_fields": True},
            ),
            "__module__": "core.fake",
        },
    )
    try:
        issues = check_serializers_pii(None)
        assert not any(i.id == "core.W007" and "AckedAllFieldsSerializer" in i.msg for i in issues)
    finally:
        del Acked


# --- Migrations pendentes ----------------------------------------------------


def test_unapplied_migrations_skipped_in_debug(settings) -> None:
    settings.DEBUG = True
    assert check_unapplied_migrations(None) == []
