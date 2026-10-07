"""importar_xml — importação dos feeds XML dos anunciantes (app ``importacao``).

Uso::

    python manage.py importar_xml --anunciante 5 --simular   # Id_Cliente do legado ou UUID
    python manage.py importar_xml --anunciante 5             # baixa, compara e aplica
    python manage.py importar_xml --anunciante 5 --sem-baixar  # reaproveita media/importacao/<id>.json
    python manage.py importar_xml --todos                    # todos, ignorando a janela noturna
    python manage.py importar_xml --janela                   # igual ao cron: para no fim da janela
"""

from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Advertiser
from importacao.services.download import ErroImportacao
from importacao.services.execucao import anunciantes_com_xml, importar_anunciante, rodar_janela


class Command(BaseCommand):
    help = "Baixa, normaliza e importa os feeds XML dos anunciantes."

    def add_arguments(self, parser):
        alvo = parser.add_mutually_exclusive_group(required=True)
        alvo.add_argument("--anunciante", help="Id_Cliente do legado ou UUID do anunciante.")
        alvo.add_argument("--todos", action="store_true", help="Todos os anunciantes com XML, sem limite de horário.")
        alvo.add_argument("--janela", action="store_true", help="Como o cron: só até o fim da janela noturna.")
        parser.add_argument("--simular", action="store_true", help="Só mostra a diferença; não grava nada.")
        parser.add_argument("--sem-baixar", action="store_true", help="Usa o JSON já baixado em vez de baixar de novo.")

    def handle(self, *args, **options):
        if options["janela"]:
            self.stdout.write(json.dumps(rodar_janela(origem="comando"), ensure_ascii=False))
            return
        if options["todos"]:
            ate = timezone.now() + timezone.timedelta(days=1)
            self.stdout.write(json.dumps(rodar_janela(ate=ate, origem="comando"), ensure_ascii=False))
            return
        adv = self._anunciante(options["anunciante"])
        try:
            r = importar_anunciante(adv, simular=options["simular"], baixar=not options["sem_baixar"], origem="comando")
        except ErroImportacao as exc:
            raise CommandError(f"{adv.name}: {exc}") from exc
        if options["simular"]:
            r = {k: v for k, v in r.items() if not isinstance(v, list)} | {
                "exemplos_alterados": r["codigos_alterados"][:10],
                "exemplos_ignorados": r["ignorados_lista"][:10],
                "exemplos_excluidos": r["codigos_excluidos"][:10],
            }
        self.stdout.write(json.dumps(r, ensure_ascii=False, indent=2, default=str))

    @staticmethod
    def _anunciante(valor):
        qs = anunciantes_com_xml() | Advertiser.objects.filter(integration__isnull=False).select_related("integration__integrator", "plan")
        try:
            adv = qs.filter(pk=uuid.UUID(valor)).first()
        except ValueError:
            adv = qs.filter(legacy_id=int(valor)).first() if valor.isdigit() else None
        if adv is None:
            raise CommandError(f"Anunciante {valor} não encontrado ou sem integração.")
        return adv
