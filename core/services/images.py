"""Miniaturas de fotos de imóveis.

Só a capa de cada imóvel ganha miniatura; o restante das fotos de anunciantes
integrados por XML é exibido direto da URL do anunciante.
"""

from __future__ import annotations

import logging
import urllib.request
from io import BytesIO

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

THUMB_SIZE = (480, 320)
DOWNLOAD_TIMEOUT = 30


def make_thumbnail(content: bytes, size: tuple[int, int] = THUMB_SIZE) -> ContentFile | None:
    """
    Gera a miniatura JPEG a partir dos bytes de uma imagem

    Args:
        content: bytes da imagem original
        size: largura e altura máximas

    Returns:
        ContentFile pronto para salvar em um ImageField, ou None se a imagem for inválida
    """
    try:
        from PIL import Image

        img = Image.open(BytesIO(content)).convert("RGB")
        img.thumbnail(size)
        out = BytesIO()
        img.save(out, format="JPEG", quality=82, optimize=True)
        return ContentFile(out.getvalue(), name="thumb.jpg")
    except Exception:  # noqa: BLE001 - miniatura é opcional, nunca derruba o fluxo
        logger.warning("Falha ao gerar miniatura", exc_info=True)
        return None


def download(url: str, timeout: int = DOWNLOAD_TIMEOUT) -> bytes | None:
    """Baixa a imagem externa; None em qualquer falha."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "portal-api"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL do anunciante
            return resp.read()
    except Exception:  # noqa: BLE001 - foto externa indisponível não é erro fatal
        logger.warning("Falha ao baixar imagem %s", url, exc_info=True)
        return None


def ensure_cover_thumbnail(photo) -> bool:
    """
    Garante a miniatura da foto de capa (hospedada ou externa)

    Args:
        photo: PropertyPhoto marcada como capa

    Returns:
        True se a miniatura existe ao final
    """
    if photo.thumbnail:
        return True
    if photo.image:
        photo.image.open("rb")
        content = photo.image.read()
        photo.image.close()
    elif photo.source_url:
        content = download(photo.source_url)
    else:
        return False
    if not content:
        return False
    thumb = make_thumbnail(content)
    if thumb is None:
        return False
    photo.thumbnail.save(thumb.name, thumb, save=True)
    return True
