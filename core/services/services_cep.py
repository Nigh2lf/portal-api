"""Cliente para a API de consulta de CEP da Noclaf.

Endpoint: ``GET {NOCLAF_API_BASE_URL}/cep/{cep}/``
Autenticação: header ``X-Api-Key`` (mesma chave usada pelo serviço de e-mail).

Uso típico (server-side):

    from core.services import lookup_cep

    data, error = lookup_cep("01310-100")
    if data:
        ...

A camada HTTP exposta em :class:`core.views.cep.CepLookupView` repassa o
resultado para o frontend sem exigir autenticação do usuário final, mas com
throttle (`scope='cep'`) para não derrubar a cota da Noclaf.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError

from django.conf import settings

logger = logging.getLogger(__name__)

_CEP_RE = re.compile(r"\D+")


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


def _build_url(cep: str) -> str:
    base = (getattr(settings, "NOCLAF_API_BASE_URL", "") or "").rstrip("/")
    return f"{base}/cep/{cep}/"


def lookup_cep(cep: str) -> tuple[dict[str, Any] | None, CepLookupError | None]:
    """Consulta a API de CEP da Noclaf.

    Retorna ``(data, None)`` em sucesso ou ``(None, CepLookupError)`` em falha.
    Nunca levanta — sempre devolve uma das duas formas.
    """
    cep_clean = normalize_cep(cep)
    if len(cep_clean) != 8:
        return None, CepLookupError(400, "CEP inválido. Informe 8 dígitos.")

    api_key = getattr(settings, "NOCLAF_API_KEY", "") or ""
    if not api_key:
        logger.warning("NOCLAF_API_KEY não configurada; consulta de CEP indisponível.")
        return None, CepLookupError(503, "Serviço de CEP não configurado.")

    url = _build_url(cep_clean)
    req = urllib.request.Request(  # noqa: S310 - URL controlada via settings
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "X-Api-Key": api_key,
        },
    )
    timeout = getattr(settings, "NOCLAF_API_TIMEOUT", 10)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read()
            try:
                parsed = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                logger.error("Resposta inválida da API de CEP: %r", body[:200])
                return None, CepLookupError(502, "Resposta inválida do serviço de CEP.")
            return parsed, None
    except HTTPError as e:
        # Tenta extrair detail do corpo de erro.
        detail = ""
        try:
            err_body = json.loads(e.read())
            detail = err_body.get("detail") or ""
        except Exception:  # noqa: BLE001, S110 - corpo opcional, segue com `detail` vazio
            pass
        if e.code == 404:
            return None, CepLookupError(404, detail or "CEP não encontrado.")
        logger.error("Noclaf CEP API HTTPError %s: %s", e.code, detail or e.reason)
        return None, CepLookupError(e.code, detail or "Erro ao consultar CEP.")
    except (URLError, TimeoutError) as e:
        logger.error("Noclaf CEP API indisponível: %s", e)
        return None, CepLookupError(503, "Serviço de CEP indisponível.")
    except Exception:  # noqa: BLE001 - nunca propagar
        logger.exception("Falha inesperada ao consultar CEP.")
        return None, CepLookupError(500, "Falha inesperada ao consultar CEP.")
