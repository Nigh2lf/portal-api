"""CEP: normalização, fallback de configuração e endpoint."""

from __future__ import annotations

from django.test import Client

from core.services import lookup_cep, normalize_cep


def test_normalize_cep_strips_mask() -> None:
    assert normalize_cep("01310-100") == "01310100"
    assert normalize_cep(" 01310 100 ") == "01310100"
    assert normalize_cep(None) == ""


def test_invalid_cep_returns_400() -> None:
    data, err = lookup_cep("123")
    assert data is None
    assert err.status == 400


def test_unconfigured_returns_503(settings) -> None:
    settings.NOCLAF_API_KEY = ""
    data, err = lookup_cep("01310-100")
    assert data is None
    assert err.status == 503


def test_endpoint_invalid_cep(client: Client) -> None:
    response = client.get("/api/v1/cep/abc/")
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
