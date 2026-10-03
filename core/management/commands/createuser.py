import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create a user with email and password"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            dest="email",
            help="Email address for the user",
        )
        parser.add_argument(
            "--password",
            dest="password",
            help="Password for the user",
        )
        parser.add_argument(
            "--role",
            dest="role",
            help="User role (must be one of User.Role values: ADMIN, USER). If omitted, ADMIN is used.",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            dest="no_input",
            help="Non-interactive mode. Will fail if email or password not provided.",
        )
        parser.add_argument(
            "--no-validate",
            action="store_true",
            dest="no_validate",
            help="Skip password validation (allows weak passwords)",
        )

    def handle(self, *args, **options):
        email = options.get("email")
        password = options.get("password")
        no_input = options.get("no_input")
        no_validate = options.get("no_validate")

        # Determine and validate user role
        user_role = options.get("role") or User.Role.ADMIN
        valid_roles = User.Role.values
        if user_role not in valid_roles:
            raise CommandError(
                f'Invalid user role "{user_role}". Valid roles are: {", ".join(valid_roles)}'
            )

        # Interactive mode
        if not no_input:
            if not email:
                email = self._get_email_input()

            if not password:
                password = self._get_password_input()

        # Validate inputs
        if not email:
            raise CommandError("Email is required")

        if not password:
            raise CommandError("Password is required")

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists')

        # Validate password strength (unless --no-validate is used)
        if not no_validate:
            try:
                validate_password(password)
            except ValidationError as e:
                raise CommandError("\n".join(e.messages)) from e

        # Create user
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
            )
            user.role = user_role
            user.is_staff = user_role == User.Role.ADMIN
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'User "{email}" created successfully with role={user_role}, is_staff={user.is_staff}.'
                )
            )
        except Exception as e:
            raise CommandError(f"Error creating user: {e!s}") from e

    def _get_email_input(self):
        """Get email from user input with validation"""
        while True:
            email = input("Email: ").strip()
            if email:
                return email
            self.stderr.write("Email cannot be empty")

    def _get_password_input(self):
        """Get password from user input with confirmation"""
        while True:
            password = getpass.getpass("Password: ")
            password2 = getpass.getpass("Password (again): ")

            if password != password2:
                self.stderr.write("Error: Your passwords didn't match.")
                continue

            if not password:
                self.stderr.write("Error: Password cannot be empty.")
                continue

            return password
