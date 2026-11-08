"""Capa dos imóveis importados: miniatura no storage e rejeição de quem ficou sem imagem.

Só a capa (a foto marcada no feed, senão a primeira) é baixada; vira miniatura
480x320 em ``properties/thumbs/`` (S3 em produção). Imóvel cuja capa não baixa ou
não é uma imagem válida **não fica no site**: é excluído (soft delete) e entra em
``RejectedProperty`` com motivo iniciado por ``PHOTO_REJECTION_PREFIX``. Essa
rejeição é automática e revista a cada importação: se a foto voltar a funcionar, o
imóvel volta e o registro some. Rejeições feitas à mão (moderação) têm outro motivo
e continuam barrando o código (ver ``apply.Applier``).
"""

from __future__ import annotations

import logging

from core.models import PropertyPhoto, RejectedProperty, XmlImportError
from core.services.images import gerar_miniaturas_capa

logger = logging.getLogger(__name__)

PHOTO_REJECTION_PREFIX = "Foto de capa indisponível"


def photo_rejection_reason(url: str) -> str:
    """Motivo gravado em ``RejectedProperty.reason`` (200 caracteres) e no erro da execução."""
    return f"{PHOTO_REJECTION_PREFIX}: {url}"[:200]


def process_cover_photos(advertiser, run=None, *, workers=3, timeout=15, progress=None) -> dict:
    """
    Gera a miniatura das capas sem miniatura do anunciante e rejeita os imóveis cuja capa falhou

    Roda depois de ``Applier.run`` gravar o feed. Capas que já têm miniatura não são
    baixadas de novo; capas que falharam em importações anteriores são tentadas de novo.

    Args:
        advertiser: anunciante recém-importado
        run: ``XmlImportRun`` da importação (recebe um ``XmlImportError`` por imóvel rejeitado)
        workers: downloads em paralelo
        timeout: segundos por download
        progress: função ``(feitas, total, ok, falhas, restante_s)`` chamada a cada 100 capas

    Returns:
        ``{"miniaturas": int, "rejeitados_sem_foto": [códigos]}``
    """
    covers = PropertyPhoto.objects.filter(
        property__advertiser=advertiser,
        property__deleted_at__isnull=True,
        is_cover=True,
        thumbnail="",
    ).select_related("property")
    failed: list = []
    thumbnails, _ = gerar_miniaturas_capa(
        covers, workers=workers, timeout=timeout, progresso=progress, failed=failed
    )
    rejected = reject_without_cover(advertiser, failed, run)
    return {"miniaturas": thumbnails, "rejeitados_sem_foto": rejected}


def reject_without_cover(advertiser, failed_photos, run=None) -> list[str]:
    """
    Tira do site os imóveis cuja capa falhou e sincroniza as rejeições automáticas do anunciante

    Args:
        advertiser: anunciante da importação
        failed_photos: ``PropertyPhoto`` de capa sem miniatura (com ``property`` carregado)
        run: execução que recebe os erros (opcional)

    Returns:
        códigos rejeitados, em ordem
    """
    reasons = {}
    for photo in failed_photos:
        prop = photo.property
        if prop.reference_code in reasons:
            continue
        reasons[prop.reference_code] = photo_rejection_reason(
            photo.source_url or (photo.image.name if photo.image else "")
        )
        if prop.deleted_at is None:
            prop.delete()  # soft delete: a próxima importação revive o imóvel se a foto voltar
    codes = sorted(reasons)

    # Rejeições automáticas de quem agora tem capa (ou saiu do feed) deixam de existir.
    RejectedProperty.objects.filter(
        advertiser=advertiser, reason__startswith=PHOTO_REJECTION_PREFIX
    ).exclude(property_reference_code__in=codes).delete()
    if not codes:
        return []

    existing = set(
        RejectedProperty.objects.filter(
            advertiser=advertiser, property_reference_code__in=codes
        ).values_list("property_reference_code", flat=True)
    )
    RejectedProperty.objects.bulk_create(
        [
            RejectedProperty(
                advertiser=advertiser, property_reference_code=code, reason=reasons[code]
            )
            for code in codes
            if code not in existing
        ],
        batch_size=500,
    )
    if run is not None:
        XmlImportError.objects.bulk_create(
            [
                XmlImportError(
                    advertiser=advertiser,
                    run=run,
                    property_reference_code=code[:45],
                    message=reasons[code],
                )
                for code in codes
            ],
            batch_size=500,
        )
    logger.info(
        "xml_import: %s imóveis de %s rejeitados sem foto de capa", len(codes), advertiser.pk
    )
    return codes
