"""import_xml — importação dos feeds XML dos anunciantes (app ``xml_import``).

Uso::

    python manage.py import_xml --advertiser 5 --simulate   # Id_Cliente do legado ou UUID
    python manage.py import_xml --advertiser 5              # baixa, compara e aplica
    python manage.py import_xml --advertiser 5 --no-download  # reaproveita media/xml_import/<id>.json
    python manage.py import_xml --all                       # todos, ignorando a janela noturna
    python manage.py import_xml --window                    # igual ao cron: para no fim da janela
    python manage.py import_xml --window --origin cron      # o que o cron dispara (pula quem já importou hoje)
    python manage.py import_xml --batch <uuid>              # roda um lote QUEUED (uso interno do painel)

O painel e o cron chamam este comando num processo separado (``services/spawn.py``): a memória
da importação volta ao sistema quando ele termina, em vez de ficar presa no worker do gunicorn.
"""

from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Advertiser, XmlImportBatch
from xml_import.services.batches import run_batch_safely
from xml_import.services.download import ImportFailed
from xml_import.services.execution import advertisers_with_xml, import_advertiser, run_window

ORIGIN_LABELS = {
    XmlImportBatch.Origin.MANUAL: "manual",
    XmlImportBatch.Origin.CRON: "cron",
    XmlImportBatch.Origin.COMMAND: "comando",
}


class Command(BaseCommand):
    help = "Baixa, normaliza e importa os feeds XML dos anunciantes."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--advertiser", help="Id_Cliente do legado ou UUID do anunciante.")
        target.add_argument(
            "--all",
            action="store_true",
            help="Todos os anunciantes com XML, sem limite de horário.",
        )
        target.add_argument(
            "--window", action="store_true", help="Como o cron: só até o fim da janela noturna."
        )
        target.add_argument("--batch", help="UUID de um lote QUEUED (disparado pelo painel).")
        parser.add_argument(
            "--origin",
            choices=("comando", "cron"),
            default="comando",
            help="Com --window: 'cron' pula anunciantes já importados hoje (padrão: comando).",
        )
        parser.add_argument(
            "--simulate", action="store_true", help="Só mostra a diferença; não grava nada."
        )
        parser.add_argument(
            "--no-download",
            action="store_true",
            help="Usa o JSON já baixado em vez de baixar de novo.",
        )

    def handle(self, *args, **options):
        if options["batch"]:
            batch = XmlImportBatch.objects.filter(pk=self._uuid(options["batch"])).first()
            if batch is None:
                raise CommandError(f"Lote {options['batch']} não encontrado.")
            label = ORIGIN_LABELS.get(batch.origin, "manual")
            summary = run_batch_safely(batch.pk, origin_label=label)
            self.stdout.write(json.dumps(summary, ensure_ascii=False, default=str))
            return
        if options["window"]:
            summary = run_window(origin_label=options["origin"])
            self.stdout.write(json.dumps(summary, ensure_ascii=False, default=str))
            return
        if options["all"]:
            until = timezone.now() + timezone.timedelta(days=1)
            self.stdout.write(
                json.dumps(run_window(until=until, origin_label="comando"), ensure_ascii=False)
            )
            return
        advertiser = self._advertiser(options["advertiser"])
        try:
            result = import_advertiser(
                advertiser,
                simulate=options["simulate"],
                download=not options["no_download"],
                origin_label="comando",
            )
        except ImportFailed as exc:
            raise CommandError(f"{advertiser.name}: {exc}") from exc
        if options["simulate"]:
            result = {k: v for k, v in result.items() if not isinstance(v, list)} | {
                "exemplos_alterados": result["codigos_alterados"][:10],
                "exemplos_ignorados": result["ignorados_lista"][:10],
                "exemplos_excluidos": result["codigos_excluidos"][:10],
            }
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    @staticmethod
    def _uuid(value):
        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise CommandError(f"Identificador inválido: {value}") from exc

    @staticmethod
    def _advertiser(value):
        qs = advertisers_with_xml() | Advertiser.objects.filter(
            integration__isnull=False
        ).select_related("integration__integrator", "plan")
        try:
            advertiser = qs.filter(pk=uuid.UUID(value)).first()
        except ValueError:
            advertiser = qs.filter(legacy_id=int(value)).first() if value.isdigit() else None
        if advertiser is None:
            raise CommandError(f"Anunciante {value} não encontrado ou sem integração.")
        return advertiser
