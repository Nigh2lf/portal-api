import os

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Registra os system checks de segurança (auditoria de permissões em ViewSets).
        from core import checks  # noqa: F401

        # Cron (APScheduler). Liga só quando RUN_CRON=true para evitar
        # duplicação no autoreload do runserver e em workers múltiplos.
        if os.environ.get("RUN_CRON", "").lower() == "true":
            from core.cron import scheduler

            scheduler.start()

        from core import signals_public_cache

        signals_public_cache.connect()

        # Auditoria de mudanças em models (CREATE/UPDATE/DELETE).
        if getattr(settings, "MODEL_AUDIT_ENABLED", False):
            from core import signals_audit

            signals_audit.connect()
