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


def nightly_xml_import() -> None:
    """Janela noturna da importação XML (app ``xml_import``); só um worker roda, os outros saem na hora.

    Por padrão roda ``manage.py import_xml --window --origin cron`` num processo separado
    (``XML_IMPORT_SUBPROCESS``), que devolve a memória ao terminar; a thread do job só espera.
    """
    from django.conf import settings

    try:
        if getattr(settings, "XML_IMPORT_SUBPROCESS", True):
            from xml_import.services.spawn import spawn_import_command

            code = spawn_import_command("--window", "--origin", "cron").wait()
            logger.info("[cron] xml_import: processo terminou com código %s", code)
            return
        from xml_import.services.execution import run_window

        logger.info("[cron] xml_import: %s", run_window())
    except Exception:  # noqa: BLE001 - erro no job não pode derrubar o scheduler
        logger.exception("[cron] xml_import falhou")
