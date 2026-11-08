"""generate_cover_thumbnails — miniatura da capa de todos os imóveis que ainda não têm; capa que falha rejeita.

Percorre os anunciantes com imóveis no ar cuja capa ainda não tem miniatura. Para cada um,
baixa a capa, gera a miniatura 480x320 e envia ao storage (S3), com a mesma regra da
importação XML (``xml_import/services/photos.py``): imóvel cuja capa não baixa ou não é
imagem válida sai do site (soft delete) e entra em ``RejectedProperty`` com o motivo
"Foto de capa indisponível"; a importação seguinte revê a rejeição. Rejeições da
moderação não são tocadas.

Cada anunciante roda sob a mesma trava da importação dele (``xml_import:<id>``): se a
importação desse anunciante estiver rodando, ele é pulado e fica para a próxima vez.

Uso::

    python manage.py generate_cover_thumbnails
    python manage.py generate_cover_thumbnails --workers 8
    python manage.py generate_cover_thumbnails --advertiser <uuid>
    python manage.py generate_cover_thumbnails --client-id 11
    python manage.py generate_cover_thumbnails --no-reject   # só gera, não rejeita ninguém
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import Advertiser, PropertyPhoto
from core.services.images import gerar_miniaturas_capa
from core.services.public_cache import invalidation_batch
from xml_import.services.lock import lock
from xml_import.services.photos import process_cover_photos


class Command(BaseCommand):
    help = (
        "Gera a miniatura da capa dos imóveis que ainda não têm e rejeita os que ficaram sem foto."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=6, help="Downloads em paralelo.")
        parser.add_argument(
            "--timeout", type=int, default=15, help="Tempo máximo de download por foto (s)."
        )
        parser.add_argument("--advertiser", help="Só este anunciante (UUID).")
        parser.add_argument("--client-id", type=int, help="Só este Id_Cliente do legado.")
        parser.add_argument(
            "--no-reject",
            action="store_true",
            help="Só gera as miniaturas; não tira do site quem ficou sem capa.",
        )

    def handle(self, *args, **options):
        covers = PropertyPhoto.objects.filter(
            is_cover=True, thumbnail="", property__deleted_at__isnull=True
        )
        if options["advertiser"]:
            covers = covers.filter(property__advertiser_id=options["advertiser"])
        if options["client_id"]:
            covers = covers.filter(property__advertiser__legacy_id=options["client_id"])
        pending = covers.count()
        self.stdout.write(f"{pending} capas sem miniatura em imóveis no ar.")
        if not pending:
            return

        if options["no_reject"]:
            self._thumbnails_only(covers, options)
            return

        advertisers = Advertiser.objects.filter(
            pk__in=covers.values("property__advertiser_id")
        ).order_by("name")
        totals = {"miniaturas": 0, "rejeitados": 0, "pulados": 0}
        for advertiser in advertisers:
            self._process_advertiser(advertiser, options, totals)

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {totals['miniaturas']} miniaturas geradas, "
                f"{totals['rejeitados']} imóveis rejeitados sem foto, "
                f"{totals['pulados']} anunciantes pulados (importação em andamento)."
            )
        )

    def _process_advertiser(self, advertiser, options, totals):
        with lock(f"xml_import:{advertiser.pk}") as acquired:
            if not acquired:
                totals["pulados"] += 1
                self.stdout.write(
                    self.style.WARNING(f"{advertiser.name}: importação em andamento, pulado.")
                )
                return
            with invalidation_batch(user="generate_cover_thumbnails"):
                summary = process_cover_photos(
                    advertiser,
                    workers=options["workers"],
                    timeout=options["timeout"],
                    progress=self._progress(advertiser.name),
                )
        rejected = summary["rejeitados_sem_foto"]
        totals["miniaturas"] += summary["miniaturas"]
        totals["rejeitados"] += len(rejected)
        self.stdout.write(
            f"{advertiser.name}: {summary['miniaturas']} miniaturas, {len(rejected)} rejeitados"
        )

    def _thumbnails_only(self, covers, options):
        photos = list(
            covers.select_related("property").order_by("property__advertiser_id", "property_id")
        )
        ok, failures = gerar_miniaturas_capa(
            photos,
            workers=options["workers"],
            timeout=options["timeout"],
            progresso=self._progress("todas"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {ok} miniaturas geradas, {failures} capas sem miniatura "
                "(foto indisponível ou inválida; nada foi rejeitado)."
            )
        )

    def _progress(self, label):
        def progress(done, total, ok, failures, remaining):
            if total >= 100:
                self.stdout.write(
                    f"  {label} [{done}/{total}] {ok} geradas, {failures} falhas "
                    f"(faltam ~{remaining / 60:.0f} min)"
                )

        return progress
