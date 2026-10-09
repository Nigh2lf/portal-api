"""Fluxo 1: baixa o feed do anunciante, normaliza e grava ``media/xml_import/<id>.json``.

O feed é baixado em blocos para um arquivo temporário (nunca inteiro na memória) e lido em
streaming por ``formats.read_file``; o arquivo é apagado ao fim.
"""

from __future__ import annotations

import hashlib
import logging
import ssl
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from xml_import import formats
from xml_import.services import files

logger = logging.getLogger(__name__)

CHUNK = 1024 * 1024


class ImportFailed(Exception):
    """Falha que impede importar o anunciante (download, formato, feed vazio)."""


@dataclass
class Downloaded:
    path: Path
    size: int
    sha256: str
    blank: bool  # só espaços em branco (ou nada)


def _download(url: str, target: Path) -> Downloaded:
    """Baixa ``url`` em blocos para ``target``, conferindo o limite de tamanho no caminho."""
    limit = settings.XML_IMPORT_MAX_MB * 1024 * 1024
    req = urllib.request.Request(  # noqa: S310 - URL cadastrada pelo admin
        url, headers={"User-Agent": "Mozilla/5.0 (portal-api xml_import)", "Accept": "*/*"}
    )

    def read(context):
        digest = hashlib.sha256()
        size, blank = 0, True
        with (
            urllib.request.urlopen(  # noqa: S310 - URL cadastrada pelo admin
                req, timeout=settings.XML_IMPORT_DOWNLOAD_TIMEOUT, context=context
            ) as resp,
            open(target, "wb") as out,
        ):
            while chunk := resp.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise ImportFailed(f"Feed maior que {settings.XML_IMPORT_MAX_MB} MB.")
                if blank and chunk.strip():
                    blank = False
                digest.update(chunk)
                out.write(chunk)
        return Downloaded(target, size, digest.hexdigest(), blank)

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
    with tempfile.NamedTemporaryFile(
        dir=files.folder(), prefix=f"{advertiser.pk}.", suffix=".xml", delete=False
    ) as tmp:
        target = Path(tmp.name)
    try:
        try:
            raw = _download(url, target)
        except ImportFailed:
            raise
        except Exception as exc:  # noqa: BLE001 - qualquer falha de rede vira erro do anunciante
            raise ImportFailed(f"Falha no download: {exc}") from exc
        if raw.blank:
            raise ImportFailed("Feed vazio.")
        expected = formats.format_for_integrator(integration.integrator)
        try:
            fmt, properties = formats.read_file(raw.path, expected)
        except formats.InvalidFormat as exc:
            raise ImportFailed(str(exc)) from exc
    finally:
        target.unlink(missing_ok=True)
    data = {
        "anunciante_id": str(advertiser.pk),
        "anunciante_legacy_id": advertiser.legacy_id,
        "url": url,
        "formato": fmt,
        "formato_esperado": expected,
        "baixado_em": timezone.now().isoformat(),
        "segundos": round(time.monotonic() - started, 1),
        "bytes": raw.size,
        "sha256": raw.sha256,
        "total": len(properties),
        "imoveis": properties,
    }
    files.save(advertiser.pk, data)
    return data
