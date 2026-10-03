"""seed_menus — cria o menu padrão do site (igual ao portal atual) em cada portal.

Idempotente: só preenche portais sem itens. Com ``--force`` apaga e recria.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Portal, PortalMenuItem

MENU_PADRAO = [
    ("Início", "/"),
    ("Imóveis", "/imoveis"),
    ("Favoritos", "/favoritos"),
    ("Imobiliárias", "/imobiliarias"),
    ("Planos", "/planos"),
    ("Blog", "/blog"),
    ("Contato", "/contato"),
]


class Command(BaseCommand):
    help = "Cria o menu padrão (Início, Imóveis, Favoritos, Imobiliárias, Planos, Blog, Contato) nos portais sem menu."

    def add_arguments(self, parser):
        parser.add_argument("--portal", help="Slug de um portal específico (default: todos).")
        parser.add_argument("--force", action="store_true", help="Apaga os itens existentes e recria o padrão.")

    @transaction.atomic
    def handle(self, *args, **options):
        portais = Portal.objects.all()
        if options["portal"]:
            portais = portais.filter(slug=options["portal"])
        criados = pulados = 0
        for portal in portais:
            if portal.menu_items.exists():
                if not options["force"]:
                    pulados += 1
                    continue
                portal.menu_items.all().delete()
            PortalMenuItem.objects.bulk_create(
                [PortalMenuItem(portal=portal, label=label, path=path, sort_order=i) for i, (label, path) in enumerate(MENU_PADRAO)]
            )
            criados += 1
            self.stdout.write(self.style.SUCCESS(f"Menu criado: {portal.slug} ({len(MENU_PADRAO)} itens)"))
        self.stdout.write(f"Resumo: {criados} portais com menu criado, {pulados} já tinham menu.")
