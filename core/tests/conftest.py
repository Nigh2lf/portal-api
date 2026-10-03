"""Fixtures compartilhadas dos testes do core."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def _sem_cache_publico(settings):
    """Cache público, fila de estatísticas e aviso ao site desligados: cada teste vê o banco direto."""
    settings.PUBLIC_CACHE_ENABLED = False
    settings.DEFERRED_WRITES_ENABLED = False
    settings.SITE_REVALIDATE_URL = ""


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
