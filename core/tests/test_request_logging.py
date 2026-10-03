"""Testes do ``RequestLoggerMiddleware`` -> ``LogRequest``."""

from __future__ import annotations

import json

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import LogRequest


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=True)
def test_excluded_paths_are_not_logged(api_client: APIClient) -> None:
    api_client.get("/api/v1/health/")
    assert LogRequest.objects.count() == 0


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=True)
def test_login_redacts_password_and_records_path_without_query(api_client: APIClient, user) -> None:
    response = api_client.post(
        "/api/v1/auth/login/?next=/dashboard",
        data={"email": user.email, "password": "Strong#Pass1234"},
        format="json",
    )
    assert response.status_code == 200

    log = LogRequest.objects.order_by("-created_at").first()
    assert log is not None
    # Path NÃO deve conter querystring
    assert log.path == "/api/v1/auth/login/"
    # Querystring vai para `params`
    assert log.params and json.loads(log.params) == {"next": "/dashboard"}
    # Body persistido com password redatada
    assert log.data is not None
    payload = json.loads(log.data)
    assert payload["email"] == user.email
    assert payload["password"] == "***"
    # Status code preservado
    assert log.status_code == 200


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=True)
def test_authorization_header_is_redacted_in_curl(api_client: APIClient, user) -> None:
    api_client.credentials(HTTP_AUTHORIZATION="Bearer super-secret-token")
    api_client.get("/api/v1/users/")

    log = LogRequest.objects.order_by("-created_at").first()
    assert log is not None
    assert log.curl is not None
    assert "super-secret-token" not in log.curl
    assert "Authorization: ***" in log.curl


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=True)
def test_authenticated_request_records_user(api_client: APIClient, admin_user) -> None:
    api_client.force_authenticate(user=admin_user)
    api_client.get("/api/v1/users/")

    log = LogRequest.objects.filter(path="/api/v1/users/").order_by("-created_at").first()
    assert log is not None
    assert log.user_id == admin_user.id
    assert log.user_email == admin_user.email


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=True)
def test_anonymous_request_has_null_user(api_client: APIClient) -> None:
    api_client.post(
        "/api/v1/auth/login/",
        data={"email": "x@example.com", "password": "wrong"},
        format="json",
    )
    log = LogRequest.objects.order_by("-created_at").first()
    assert log is not None
    assert log.user_id is None
    assert log.user_email == ""


@pytest.mark.django_db
@override_settings(LOG_REQUESTS_ENABLED=False)
def test_disabled_middleware_writes_nothing(api_client: APIClient) -> None:
    api_client.post(
        "/api/v1/auth/login/",
        data={"email": "x@example.com", "password": "wrong"},
        format="json",
    )
    assert LogRequest.objects.count() == 0
