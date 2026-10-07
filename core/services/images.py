"""Miniaturas de fotos de imóveis.

Só a capa de cada imóvel ganha miniatura; o restante das fotos de anunciantes
integrados por XML é exibido direto da URL do anunciante.
"""

from __future__ import annotations

import logging
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def gerar_miniaturas_capa(fotos, workers: int = 6, timeout: int = 15, progresso=None, lote: int = 200) -> tuple[int, int]:
    """
    Gera a miniatura de várias capas: download, redimensionamento e upload em threads

    O banco é atualizado só pela thread que chamou, em lotes: as threads não abrem
    conexão própria (o MySQL do Railway aceita poucas conexões).

    Args:
        fotos: PropertyPhoto de capa sem miniatura (com ``property`` carregado)
        workers: downloads em paralelo
        timeout: segundos por download
        progresso: função ``(feitas, total, ok, falhas, restante_s)`` chamada a cada 100
        lote: tamanho do ``bulk_update``

    Returns:
        (geradas, falhas)
    """
    from core.models import PropertyPhoto

    fotos = list(fotos)
    total = len(fotos)
    if not total:
        return 0, 0
    campo = PropertyPhoto._meta.get_field("thumbnail")
    ok = falhas = 0
    pendentes = []
    inicio = time.monotonic()

    def processar(foto):
        if foto.image:
            with foto.image.open("rb") as f:
                conteudo = f.read()
        else:
            conteudo = download(foto.source_url, timeout=timeout) if foto.source_url else None
        thumb = make_thumbnail(conteudo) if conteudo else None
        if thumb is None:
            return foto, None
        return foto, campo.storage.save(campo.generate_filename(foto, thumb.name), thumb)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futuros = [pool.submit(processar, foto) for foto in fotos]
        for n, futuro in enumerate(as_completed(futuros), 1):
            try:
                foto, nome = futuro.result()
            except Exception:  # noqa: BLE001 - uma foto com problema não interrompe as demais
                logger.warning("Falha ao gerar miniatura", exc_info=True)
                falhas += 1
                continue
            if nome:
                foto.thumbnail.name = nome
                pendentes.append(foto)
                ok += 1
            else:
                falhas += 1
            if len(pendentes) >= lote:
                PropertyPhoto.objects.bulk_update(pendentes, ["thumbnail"], batch_size=lote)
                pendentes = []
            if progresso and (n % 100 == 0 or n == total):
                progresso(n, total, ok, falhas, (time.monotonic() - inicio) / n * (total - n))
    if pendentes:
        PropertyPhoto.objects.bulk_update(pendentes, ["thumbnail"], batch_size=lote)
    return ok, falhas
