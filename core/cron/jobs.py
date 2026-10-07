"""Jobs agendados.

Cada função aqui é um job standalone — sem args, sem return, captura suas
próprias exceções. APScheduler chama essas funções de acordo com o agendamento
definido em ``core.cron.scheduler.start``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def heartbeat() -> None:
    """Job de exemplo. Substitua/adicione os seus em ``scheduler.start``."""
    logger.info("cron heartbeat ok")


def purge_old_request_logs() -> None:
    """Apaga ``LogRequest`` com mais de ``LOG_REQUESTS_RETENTION_DAYS`` dias.

    Sem isso a tabela cresce indefinidamente. Default 30 dias.
    """
    try:
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        from core.models import LogRequest

        days = int(getattr(settings, "LOG_REQUESTS_RETENTION_DAYS", 30))
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = LogRequest.objects.filter(created_at__lt=cutoff).delete()
        if deleted:
            logger.info("purge_old_request_logs: %d registros removidos", deleted)
    except Exception:
        logger.exception("purge_old_request_logs falhou")


def purge_old_audit_logs() -> None:
    """Apaga ``LogModelChange`` com mais de ``MODEL_AUDIT_RETENTION_DAYS`` dias.

    Sem isso a tabela cresce indefinidamente. Default 30 dias.
    """
    try:
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        from core.models import LogModelChange

        days = int(getattr(settings, "MODEL_AUDIT_RETENTION_DAYS", 30))
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = LogModelChange.objects.filter(created_at__lt=cutoff).delete()
        if deleted:
            logger.info("purge_old_audit_logs: %d registros removidos", deleted)
    except Exception:
        logger.exception("purge_old_audit_logs falhou")


def importar_xml_noturno() -> None:
    """Janela noturna da importação XML (app ``importacao``); só um worker roda, os outros saem na hora."""
    from importacao.services.execucao import rodar_janela

    try:
        logger.info("[cron] importacao_xml: %s", rodar_janela())
    except Exception:  # noqa: BLE001 - erro no job não pode derrubar o scheduler
        logger.exception("[cron] importacao_xml falhou")
