"""generate_cover_thumbnails — gera a miniatura da foto de capa dos imóveis que ainda não têm.

Roda depois do ``import_legacy``: a importação só registra os links das fotos. Baixa a
capa de cada imóvel, gera a miniatura 480x320 e envia ao storage (S3). A importação
XML (app ``importacao``) usa a mesma rotina para as capas novas de cada anunciante.

Uso::

    python manage.py generate_cover_thumbnails
    python manage.py generate_cover_thumbnails --workers 8 --limit 500
    python manage.py generate_cover_thumbnails --client-id 11
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import PropertyPhoto
from core.services.images import gerar_miniaturas_capa


class Command(BaseCommand):
    help = "Gera a miniatura da capa dos imóveis que ainda não têm (fotos externas ou hospedadas)."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=6, help="Downloads em paralelo.")
        parser.add_argument("--limit", type=int, default=0, help="Máximo de capas nesta execução (0 = todas).")
        parser.add_argument("--client-id", type=int, help="Só os imóveis deste Id_Cliente do legado.")
        parser.add_argument("--timeout", type=int, default=15, help="Tempo máximo de download por foto (s).")

    def handle(self, *args, **options):
        qs = (
            PropertyPhoto.objects.filter(is_cover=True, thumbnail="")
            .select_related("property")
            .order_by("property__advertiser_id", "property_id")
        )
        if options["client_id"]:
            qs = qs.filter(property__advertiser__legacy_id=options["client_id"])
        if options["limit"]:
            qs = qs[: options["limit"]]
        fotos = list(qs)
        self.stdout.write(f"{len(fotos)} capas sem miniatura.")

        def progresso(n, total, ok, falhas, restante):
            self.stdout.write(f"[{n}/{total}] {ok} geradas, {falhas} falhas (faltam ~{restante / 60:.0f} min)")

        ok, falhas = gerar_miniaturas_capa(fotos, workers=options["workers"], timeout=options["timeout"], progresso=progresso)
        self.stdout.write(self.style.SUCCESS(f"Concluído: {ok} miniaturas geradas, {falhas} capas sem miniatura (foto indisponível ou inválida)."))
