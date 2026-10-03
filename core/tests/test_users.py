"""Modelo User: normalização de e-mail, soft delete, verificação de e-mail."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_email_is_normalized_to_lowercase() -> None:
    u = User.objects.create_user(email="Foo@Example.COM", password="Strong#Pass1234")
    assert u.email == "foo@example.com"


@pytest.mark.django_db
def test_set_password_clears_forgot_token() -> None:
    u = User.objects.create_user(email="a@b.com", password="Strong#Pass1234")
    u.forgot_password_hash = "tok"
    u.save()

    u.set_password("Outra#Senha9999")
    u.save()
    u.refresh_from_db()

    assert u.forgot_password_hash is None


@pytest.mark.django_db
def test_soft_delete_sets_inactive_and_timestamp() -> None:
    u = User.objects.create_user(email="x@y.com", password="Strong#Pass1234")
    u.delete()
    u.refresh_from_db()

    assert u.is_active is False
    assert u.deleted_at is not None


# --- Verificação de e-mail (opt-in) -----------------------------------------


@pytest.mark.django_db
def test_generate_and_confirm_email_verification_code() -> None:
    u = User.objects.create_user(email="v@x.com", password="Strong#Pass1234")
    code = u.generate_email_verification_code()
    u.save()

    assert len(code) == 6
    assert code.isdigit()
    assert u.email_verified is False

    assert u.confirm_email_verification(code) is True
    u.refresh_from_db()
    assert u.email_verified is True
    assert u.email_verification_code is None


@pytest.mark.django_db
def test_confirm_email_verification_rejects_wrong_code() -> None:
    u = User.objects.create_user(email="w@x.com", password="Strong#Pass1234")
    u.generate_email_verification_code()
    u.save()

    assert u.confirm_email_verification("000000") is False
    u.refresh_from_db()
    assert u.email_verified is False
