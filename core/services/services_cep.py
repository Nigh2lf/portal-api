"""Consulta de CEP na ViaCEP com cache em banco (``PostalCode``).

Fluxo: normaliza o CEP → procura em ``PostalCode`` (válido por
``CEP_CACHE_DAYS``) → se não houver, ``GET https://viacep.com.br/ws/{cep}/json/``
e grava o resultado. A resposta ao front mantém o formato
``{cep, logradouro, bairro, cidade, uf}`` (ver ``docs/cep.md``).
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from datetime import timedelta
from typing import Any
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_CEP_RE = re.compile(r"\D+")
VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"


class CepLookupError(Exception):
    """Erro normalizado da consulta de CEP."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def normalize_cep(cep: str | None) -> str:
    """Remove tudo que não é dígito. Retorna string vazia se inválido."""
    if not cep:
        return ""
    return _CEP_RE.sub("", cep)[:8]


def format_cep(cep: str) -> str:
    return f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep


def _payload(cep: str, street: str, neighborhood: str, city: str, state_code: str) -> dict[str, Any]:
    return {"cep": format_cep(cep), "logradouro": street, "bairro": neighborhood, "cidade": city, "uf": state_code}


def _from_cache(cep: str) -> dict[str, Any] | None:
    from core.models import PostalCode

    dias = int(getattr(settings, "CEP_CACHE_DAYS", 365))
    registro = PostalCode.objects.filter(cep=cep).first()
    if registro is None:
        return None
    if dias and registro.fetched_at < timezone.now() - timedelta(days=dias):
        return None
    if registro.not_found:
        raise CepLookupError(404, "CEP não encontrado.")
    return _payload(cep, registro.street, registro.neighborhood, registro.city, registro.state_code)


def _save_cache(cep: str, data: dict[str, Any] | None) -> None:
    from core.models import PostalCode

    try:
        PostalCode.objects.update_or_create(
            cep=cep,
            defaults={
                "street": (data or {}).get("logradouro", "") or "",
                "complement": (data or {}).get("complemento", "") or "",
                "neighborhood": (data or {}).get("bairro", "") or "",
                "city": (data or {}).get("localidade", "") or "",
                "state_code": (data or {}).get("uf", "") or "",
                "ibge_code": (data or {}).get("ibge", "") or "",
                "raw": data or {},
                "not_found": data is None,
                "fetched_at": timezone.now(),
            },
        )
    except Exception:  # noqa: BLE001 - cache é otimização; falha não pode quebrar a consulta
        logger.warning("Falha ao gravar cache de CEP %s", cep, exc_info=True)


def _fetch_viacep(cep: str) -> dict[str, Any] | None:
    """Consulta a ViaCEP. Retorna o JSON, None quando o CEP não existe; levanta CepLookupError em falha."""
    url = getattr(settings, "VIACEP_URL", VIACEP_URL).format(cep=cep)
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json", "User-Agent": "portal-api"})  # noqa: S310
    timeout = int(getattr(settings, "CEP_API_TIMEOUT", 10))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read()
    except HTTPError as e:
        if e.code == 400:
            raise CepLookupError(400, "CEP inválido. Informe 8 dígitos.") from e
        logger.error("ViaCEP HTTPError %s: %s", e.code, e.reason)
        raise CepLookupError(502, "Erro ao consultar CEP.") from e
    except (URLError, TimeoutError) as e:
        logger.error("ViaCEP indisponível: %s", e)
        raise CepLookupError(503, "Serviço de CEP indisponível.") from e
    try:
        parsed = json.loads(body)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("Resposta inválida da ViaCEP: %r", body[:200])
        raise CepLookupError(502, "Resposta inválida do serviço de CEP.") from e
    if not isinstance(parsed, dict) or parsed.get("erro"):
        return None
    return parsed


def lookup_cep(cep: str) -> tuple[dict[str, Any] | None, CepLookupError | None]:
    """
    Consulta o CEP (cache em banco, depois ViaCEP)

    Args:
        cep: CEP com ou sem formatação

    Returns:
        ``(data, None)`` em sucesso ou ``(None, CepLookupError)`` em falha; nunca levanta
    """
    cep_clean = normalize_cep(cep)
    if len(cep_clean) != 8:
        return None, CepLookupError(400, "CEP inválido. Informe 8 dígitos.")
    try:
        cached = _from_cache(cep_clean)
    except CepLookupError as e:
        return None, e
    except Exception:  # noqa: BLE001 - banco indisponível não impede a consulta externa
        logger.warning("Falha ao ler cache de CEP", exc_info=True)
        cached = None
    if cached:
        return cached, None
    try:
        data = _fetch_viacep(cep_clean)
    except CepLookupError as e:
        return None, e
    except Exception:  # noqa: BLE001 - nunca propagar
        logger.exception("Falha inesperada ao consultar CEP.")
        return None, CepLookupError(500, "Falha inesperada ao consultar CEP.")
    _save_cache(cep_clean, data)
    if data is None:
        return None, CepLookupError(404, "CEP não encontrado.")
    return _payload(cep_clean, data.get("logradouro", ""), data.get("bairro", ""), data.get("localidade", ""), data.get("uf", "")), None
