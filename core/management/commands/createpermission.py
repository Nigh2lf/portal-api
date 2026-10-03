from django.core.management.base import BaseCommand, CommandError

from core.models import Menu, Permission


class Command(BaseCommand):
    help = "Create a new Menu with name and view, and automatically create permissions (READ, CREATE, UPDATE, DELETE)"

    def add_arguments(self, parser):
        parser.add_argument(
            "types",
            nargs="*",
            help="Permission types to create (READ, CREATE, UPDATE, DELETE). If not provided, all 4 permissions will be created.",
        )
        parser.add_argument(
            "--name",
            dest="name",
            help="Name of the menu",
        )
        parser.add_argument(
            "--view",
            dest="view",
            help="View path for the menu (optional)",
        )

    def handle(self, *args, **options):
        name = options.get("name")
        view = options.get("view")
        types = options.get("types", [])

        # Validate permission types if provided
        valid_types = ["READ", "CREATE", "UPDATE", "DELETE"]
        if types:
            invalid_types = [t for t in types if t not in valid_types]
            if invalid_types:
                raise CommandError(
                    f'Invalid permission types: {", ".join(invalid_types)}. '
                    f'Valid types are: {", ".join(valid_types)}'
                )

        # Interactive mode (always)
        if not name:
            name = self._get_name_input()

        if not view:
            view = self._get_view_input()

        # Validate inputs
        if not name:
            raise CommandError("Name is required")

        # Check if menu with same name already exists
        if Menu.objects.filter(name=name).exists():
            raise CommandError(f'Menu with name "{name}" already exists')

        # Create menu
        try:
            menu = Menu.objects.create(name=name, view=view if view else None)

            msg = f'Menu "{name}" created successfully (ID: {menu.id})'
            if view:
                msg += f' with view="{view}"'

            self.stdout.write(self.style.SUCCESS(msg))

            # Create permissions for the menu
            self._create_permissions(menu, types if types else valid_types)

        except Exception as e:
            raise CommandError(f"Error creating menu: {e!s}") from e

    def _get_name_input(self):
        """Get name from user input with validation"""
        while True:
            name = input("Menu name: ").strip()
            if name:
                return name
            self.stderr.write("Name cannot be empty")

    def _get_view_input(self):
        """Get view from user input (optional)"""
        view = input("View path (optional, press Enter to skip): ").strip()
        return view if view else None

    def _create_permissions(self, menu, types_to_create):
        """Create permissions for the menu based on specified types"""
        all_permission_types = {
            "READ": f"Leitura de {menu.name}",
            "CREATE": f"Criar {menu.name}",
            "UPDATE": f"Atualizar {menu.name}",
            "DELETE": f"Deletar {menu.name}",
        }

        # Filter to only create requested types
        permission_types = [
            (ptype, pname)
            for ptype, pname in all_permission_types.items()
            if ptype in types_to_create
        ]

        created_count = 0
        total = len(permission_types)

        for perm_type, perm_name in permission_types:
            try:
                permission = Permission.objects.create(menu=menu, name=perm_name, type=perm_type)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Permission created: {perm_type} - "{perm_name}" (ID: {permission.id})'
                    )
                )
                created_count += 1
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(f"  ✗ Error creating permission {perm_type}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nTotal: {created_count}/{total} permissions created successfully")
        )
