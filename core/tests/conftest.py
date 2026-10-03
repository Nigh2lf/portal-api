"""Fixtures compartilhadas dos testes do core."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    """Cliente DRF sem autenticação."""
    return APIClient()


@pytest.fixture
def user(db):
    """Usuário comum (role USER) já persistido."""
    return User.objects.create_user(email="user@example.com", password="Strong#Pass1234")


@pytest.fixture
def admin_user(db):
    """Superuser com role ADMIN, pronto para acessar /schema/ e admin."""
    u = User.objects.create_superuser(email="admin@example.com", password="Strong#Pass1234")
    u.is_staff = True
    u.role = User.Role.ADMIN
    u.save()
    return u
