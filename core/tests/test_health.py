"""Health-check, acesso aos docs e formato do envelope."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_ok(client: Client) -> None:
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert isinstance(body["response_time_ms"], int)


def test_schema_requires_admin(client: Client) -> None:
    response = client.get("/api/v1/schema/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_schema_ok_with_admin(admin_user) -> None:
    c = Client()
    c.force_login(admin_user)
    response = c.get("/api/v1/schema/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_unauth_request_uses_envelope(client: Client) -> None:
    """Endpoint protegido sem credenciais responde no envelope padronizado."""
    response = client.get("/api/v1/users/")
    assert response.status_code == 401
    body = response.json()
    assert set(body) == {"success", "status", "message", "data", "error"}
    assert body["success"] is False
