"""seed_advertiser_profile — cria os Menus + Permissions dos ``view_name`` do app
``advertiser`` (que não passam pelo router do ``core``) e os vincula ao perfil
``ANUNCIANTE``.

Idempotente: usa get_or_create.
"""

from django.core.management.base import BaseCommand

from core.management.commands.seedpermissions import PERMISSION_DEFAULTS
from core.models import Menu, Permission, ProfilePermission
from core.services.advertiser_access import get_advertiser_profile

ADVERTISER_MENUS = {
    "advertiser_me": "Anunciante - Meus dados",
    "advertiser_property": "Anunciante - Imóveis",
    "advertiser_inquiry": "Anunciante - Ofertas recebidas",
    "advertiser_property_request": "Anunciante - Encomendas",
    "advertiser_stats": "Anunciante - Estatísticas",
    "advertiser_import": "Anunciante - Relatório de importação",
}


class Command(BaseCommand):
    help = "Cria Menus/Permissions do app advertiser e os vincula ao perfil ANUNCIANTE."

    def handle(self, *args, **options):
        profile = get_advertiser_profile()
        created_menus = created_perms = linked = 0

        for view_name, menu_name in ADVERTISER_MENUS.items():
            menu, menu_created = Menu.objects.get_or_create(
                view=view_name, defaults={"name": menu_name}
            )
            created_menus += menu_created
            for ptype, label in PERMISSION_DEFAULTS.items():
                permission, perm_created = Permission.objects.get_or_create(
                    menu=menu, type=ptype, defaults={"name": label.format(name=menu.name)}
                )
                created_perms += perm_created
                _, link_created = ProfilePermission.objects.get_or_create(
                    profile=profile, permission=permission
                )
                linked += link_created
            self.stdout.write(f"{view_name}: menu {'criado' if menu_created else 'existente'}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nResumo: {created_menus} menus criados, {created_perms} permissões criadas, "
                f"+{linked} vínculos no perfil {profile.name}."
            )
        )
