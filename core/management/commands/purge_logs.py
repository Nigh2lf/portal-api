"""Apaga registros antigos das tabelas que só crescem.

Não há agendador no projeto: rode à mão ou por um agendador externo.

    python manage.py purge_logs
    python manage.py purge_logs --dry-run
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import LogModelChange, LogRequest, SearchLog

RETENTIONS = (
    (LogRequest, "LOG_REQUESTS_RETENTION_DAYS", 30),
    (LogModelChange, "MODEL_AUDIT_RETENTION_DAYS", 30),
    (SearchLog, "SEARCH_LOG_RETENTION_DAYS", 120),
)


class Command(BaseCommand):
    help = "Apaga LogRequest, LogModelChange e SearchLog mais antigos que a retenção configurada."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Só conta, não apaga.")

    def handle(self, *args, **options):
        for model, setting, default in RETENTIONS:
            days = int(getattr(settings, setting, default))
            old = model.objects.filter(created_at__lt=timezone.now() - timedelta(days=days))
            total = old.count() if options["dry_run"] else old.delete()[0]
            self.stdout.write(f"{model.__name__}: {total} registros com mais de {days} dias")
