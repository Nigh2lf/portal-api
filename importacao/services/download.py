"""Fluxo 1: baixa o feed do anunciante, normaliza e grava ``media/importacao/<id>.json``."""

from __future__ import annotations

import hashlib
import logging
import ssl
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

from importacao import formatos
from importacao.services import arquivos

logger = logging.getLogger(__name__)


class ErroImportacao(Exception):
    """Falha que impede importar o anunciante (download, formato, feed vazio)."""


def _baixar(url: str) -> bytes:
    limite = settings.IMPORTACAO_MAX_MB * 1024 * 1024
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (portal-api importacao)", "Accept": "*/*"})

    def ler(contexto):
        with urllib.request.urlopen(req, timeout=settings.IMPORTACAO_TIMEOUT_DOWNLOAD, context=contexto) as resp:  # noqa: S310 - URL cadastrada pelo admin
            corpo = resp.read(limite + 1)
        if len(corpo) > limite:
            raise ErroImportacao(f"Feed maior que {settings.IMPORTACAO_MAX_MB} MB.")
        return corpo

    try:
        return ler(None)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            # Vários hosts de integradores têm certificado vencido; o legado também não verificava.
            logger.warning("importacao: SSL inválido em %s, baixando sem verificar", url)
            return ler(ssl._create_unverified_context())  # noqa: S323
        raise ErroImportacao(f"Falha no download: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ErroImportacao("Tempo esgotado no download.") from exc


def baixar_e_normalizar(advertiser) -> dict:
    """
    Baixa o feed, converte para o formato normalizado e grava o JSON do anunciante

    Args:
        advertiser: anunciante com integração XML

    Returns:
        o conteúdo gravado (metadados + ``imoveis``)
    """
    integracao = getattr(advertiser, "integration", None)
    url = (integracao.xml_url if integracao else "").strip()
    if not url:
        raise ErroImportacao("Anunciante sem URL de XML.")
    inicio = time.monotonic()
    try:
        bruto = _baixar(url)
    except ErroImportacao:
        raise
    except Exception as exc:  # noqa: BLE001 - qualquer falha de rede vira erro do anunciante
        raise ErroImportacao(f"Falha no download: {exc}") from exc
    if not bruto.strip():
        raise ErroImportacao("Feed vazio.")
    esperado = formatos.formato_do_integrador(integracao.integrator)
    try:
        formato, imoveis = formatos.ler(bruto, esperado)
    except formatos.FormatoInvalido as exc:
        raise ErroImportacao(str(exc)) from exc
    dados = {
        "anunciante_id": str(advertiser.pk),
        "anunciante_legacy_id": advertiser.legacy_id,
        "url": url,
        "formato": formato,
        "formato_esperado": esperado,
        "baixado_em": timezone.now().isoformat(),
        "segundos": round(time.monotonic() - inicio, 1),
        "bytes": len(bruto),
        "sha256": hashlib.sha256(bruto).hexdigest(),
        "total": len(imoveis),
        "imoveis": imoveis,
    }
    arquivos.salvar(advertiser.pk, dados)
    return dados
