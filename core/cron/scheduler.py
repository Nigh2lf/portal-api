"""Bootstrap do APScheduler.

Chamado por ``core.apps.CoreConfig.ready`` quando ``RUN_CRON=true``.

⚠️  Atenção em deploy:
- ``runserver`` com autoreload cria 2 processos -> o cron rodaria em duplicidade.
  Mantenha ``RUN_CRON`` desligado em dev e use um worker dedicado em produção.
- Com gunicorn/uvicorn multi-worker, ligue ``RUN_CRON=true`` em **apenas um**
  processo (ex.: container/worker separado), nunca em todos.

Como adicionar um job novo:
    from core.cron.jobs import meu_job
    scheduler.add_job(meu_job, "interval", minutes=5, id="meu_job", replace_existing=True)
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

from core.cron.jobs import (
    heartbeat,
    nightly_xml_import,
    purge_old_audit_logs,
    purge_old_request_logs,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _parse_hm(value: str, default_hour: int, default_minute: int) -> tuple[int, int]:
    """Parseia ``"HH:MM"`` em ``(hour, minute)``. Em caso de erro, usa default."""
    try:
        hour_str, minute_str = str(value).split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, AttributeError):
        pass
    logger.warning(
        "Schedule inválido %r, usando default %02d:%02d",
        value,
        default_hour,
        default_minute,
    )
    return default_hour, default_minute


def start() -> BackgroundScheduler:
    """Inicia o scheduler (idempotente). Retorna a instância em uso."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")

    req_hour, req_minute = _parse_hm(
        getattr(settings, "LOG_REQUESTS_PURGE_SCHEDULE", "03:00"), 3, 0
    )
    audit_hour, audit_minute = _parse_hm(
        getattr(settings, "MODEL_AUDIT_PURGE_SCHEDULE", "03:15"), 3, 15
    )

    # === Registre seus jobs aqui ===========================================
    scheduler.add_job(
        heartbeat,
        trigger="interval",
        minutes=60,
        id="heartbeat",
        replace_existing=True,
    )
    scheduler.add_job(
        purge_old_request_logs,
        trigger="cron",
        hour=req_hour,
        minute=req_minute,
        id="purge_old_request_logs",
        replace_existing=True,
    )
    scheduler.add_job(
        purge_old_audit_logs,
        trigger="cron",
        hour=audit_hour,
        minute=audit_minute,
        id="purge_old_audit_logs",
        replace_existing=True,
    )
    imp_hour, imp_minute = _parse_hm(getattr(settings, "XML_IMPORT_WINDOW_START", "01:00"), 1, 0)
    scheduler.add_job(
        nightly_xml_import,
        trigger="cron",
        hour=imp_hour,
        minute=imp_minute,
        # A janela é no horário de Brasília; o scheduler roda em UTC.
        timezone="America/Sao_Paulo",
        id="nightly_xml_import",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # =======================================================================

    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler iniciado com %d job(s)", len(scheduler.get_jobs()))
    return scheduler
