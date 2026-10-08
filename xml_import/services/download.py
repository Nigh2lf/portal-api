"""Fluxo 1: baixa o feed do anunciante, normaliza e grava ``media/xml_import/<id>.json``."""

from __future__ import annotations

import hashlib
import logging
import ssl
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

from xml_import import formats
from xml_import.services import files

logger = logging.getLogger(__name__)


class ImportFailed(Exception):
    """Falha que impede importar o anunciante (download, formato, feed vazio)."""


def _download(url: str) -> bytes:
    limit = settings.XML_IMPORT_MAX_MB * 1024 * 1024
    req = urllib.request.Request(  # noqa: S310 - URL cadastrada pelo admin
        url, headers={"User-Agent": "Mozilla/5.0 (portal-api xml_import)", "Accept": "*/*"}
    )

    def read(context):
        with urllib.request.urlopen(  # noqa: S310 - URL cadastrada pelo admin
            req, timeout=settings.XML_IMPORT_DOWNLOAD_TIMEOUT, context=context
        ) as resp:
            body = resp.read(limit + 1)
        if len(body) > limit:
            raise ImportFailed(f"Feed maior que {settings.XML_IMPORT_MAX_MB} MB.")
        return body

    try:
        return read(None)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            # Vários hosts de integradores têm certificado vencido; o legado também não verificava.
            logger.warning("xml_import: SSL inválido em %s, baixando sem verificar", url)
            return read(ssl._create_unverified_context())  # noqa: S323
        raise ImportFailed(f"Falha no download: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ImportFailed("Tempo esgotado no download.") from exc


def download_and_normalize(advertiser) -> dict:
    """
    Baixa o feed, converte para o formato normalizado e grava o JSON do anunciante

    Args:
        advertiser: anunciante com integração XML

    Returns:
        o conteúdo gravado (metadados + ``imoveis``)
    """
    integration = getattr(advertiser, "integration", None)
    url = (integration.xml_url if integration else "").strip()
    if not url:
        raise ImportFailed("Anunciante sem URL de XML.")
    started = time.monotonic()
    try:
        raw = _download(url)
    except ImportFailed:
        raise
    except Exception as exc:  # noqa: BLE001 - qualquer falha de rede vira erro do anunciante
        raise ImportFailed(f"Falha no download: {exc}") from exc
    if not raw.strip():
        raise ImportFailed("Feed vazio.")
    expected = formats.format_for_integrator(integration.integrator)
    try:
        fmt, properties = formats.read(raw, expected)
    except formats.InvalidFormat as exc:
        raise ImportFailed(str(exc)) from exc
    data = {
        "anunciante_id": str(advertiser.pk),
        "anunciante_legacy_id": advertiser.legacy_id,
        "url": url,
        "formato": fmt,
        "formato_esperado": expected,
        "baixado_em": timezone.now().isoformat(),
        "segundos": round(time.monotonic() - started, 1),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "total": len(properties),
        "imoveis": properties,
    }
    files.save(advertiser.pk, data)
    return data
