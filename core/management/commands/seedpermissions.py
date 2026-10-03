"""seedpermissions — varre os ViewSets registrados no router e cria
Menus + Permissions automaticamente, baseando-se em ``view_name``
declarado em cada ViewSet.

Também garante o perfil ``ADMIN`` com todas as permissões vinculadas.

Idempotente: usa get_or_create.
"""

from django.core.management.base import BaseCommand

from core.models import Menu, Permission, Profile, ProfilePermission

PERMISSION_DEFAULTS = {
    "READ": "Leitura de {name}",
    "CREATE": "Criar {name}",
    "UPDATE": "Atualizar {name}",
    "DELETE": "Deletar {name}",
}


class Command(BaseCommand):
    help = "Cria Menus e Permissions a partir dos ViewSets registrados em config/urls_v1.py."

    def add_arguments(self, parser):
        parser.add_argument(
            "--types",
            nargs="+",
            default=list(PERMISSION_DEFAULTS.keys()),
            help="Tipos de permissão a criar (default: todos).",
        )

    def handle(self, *args, **options):
        # Import tardio para evitar ciclos.
        from config.urls_v1 import router

        types = options["types"]
        invalid = [t for t in types if t not in PERMISSION_DEFAULTS]
        if invalid:
            self.stderr.write(
                self.style.ERROR(
                    f"Tipos inválidos: {invalid}. Válidos: {list(PERMISSION_DEFAULTS)}"
                )
            )
            return

        created_menus = 0
        created_perms = 0
        skipped = []

        for prefix, viewset, basename in router.registry:
            view_name = getattr(viewset, "view_name", None) or basename

            menu, was_created = Menu.objects.get_or_create(
                view=view_name,
                defaults={"name": view_name},
            )
            if was_created:
                created_menus += 1
                self.stdout.write(self.style.SUCCESS(f"Menu criado: {view_name} (/{prefix}/)"))
            else:
                skipped.append(view_name)

            for ptype in types:
                pname = PERMISSION_DEFAULTS[ptype].format(name=menu.name)
                _, p_created = Permission.objects.get_or_create(
                    menu=menu,
                    type=ptype,
                    defaults={"name": pname},
                )
                if p_created:
                    created_perms += 1

        linked = self._sync_admin_profile()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nResumo: {created_menus} menus criados, {created_perms} permissões criadas. "
                f"Já existiam: {len(skipped)}. Perfil ADMIN: +{linked} permissões vinculadas."
            )
        )

    def _sync_admin_profile(self):
        """Garante o perfil ADMIN com todas as permissões existentes."""
        profile, _ = Profile.objects.get_or_create(name="ADMIN", defaults={"is_active": True})
        already = set(
            ProfilePermission.objects.filter(profile=profile).values_list(
                "permission_id", flat=True
            )
        )
        missing = Permission.objects.exclude(id__in=already)
        ProfilePermission.objects.bulk_create(
            [ProfilePermission(profile=profile, permission=perm) for perm in missing]
        )
        return len(missing)
