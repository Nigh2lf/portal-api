from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Registra os system checks de segurança (auditoria de permissões em ViewSets).
        from core import (
            checks,  # noqa: F401
            signals_public_cache,
        )

        signals_public_cache.connect()

        # Auditoria de mudanças em models (CREATE/UPDATE/DELETE).
        if getattr(settings, "MODEL_AUDIT_ENABLED", False):
            from core import signals_audit

            signals_audit.connect()
