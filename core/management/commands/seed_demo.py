"""Comando ``seed_demo`` — popula banco com dados mínimos para um dev novo
conseguir logar e testar a API em segundos.

Uso::

    python manage.py seed_demo

Cria três usuários (idempotente — roda quantas vezes quiser):

1. **Superuser do Django Admin** — ``admin@admin.com`` / senha ``admin``
   (texto puro, **sem MD5**). Usado para entrar em ``/admin/``. ``is_staff``
   e ``is_superuser`` ligados, role ``ADMIN``.

2. **Admin da API** — ``admin@<projeto>.com`` / senha ``admin`` no front
   (MD5↑). Role ``ADMIN``, ``is_staff=False``. Faz login via API normal.
   ``<projeto>`` vem de ``PROJECT_NAME`` (slug em lowercase).

3. **Usuário comum da API** — ``a@a.com`` / senha ``a`` no front (MD5↑).
   Role ``USER``.

Convenção Noclaf de senha (vale só para os usuários da API)
-----------------------------------------------------------
O front sempre envia a senha em MD5 hex (uppercase). O backend trata esse
hash como "senha bruta" e o Django aplica PBKDF2 por cima. Para gravar,
fazemos ``set_password(md5_upper(senha_humana))``. Exemplos:

- ``MD5("admin").upper()`` = ``21232F297A57A5A743894A0E4A801FC3``
- ``MD5("a").upper()``     = ``0CC175B9C0F1B6A831C399E269772661``

O **superuser do Django Admin** é exceção: o ``/admin/`` não passa pelo
front Noclaf, então ele recebe a senha "admin" em texto puro
(``set_password("admin")``).

⚠️ Não rodar em produção. O comando aborta se ``DEBUG=False``, a menos que
você passe ``--force``.
"""

from __future__ import annotations

import hashlib
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


def md5_upper(raw: str) -> str:
    """MD5 hex em maiúsculas — replica o que o front Noclaf envia."""
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()  # noqa: S324 - exigência do front


def project_slug() -> str:
    """Slug minimalista de ``PROJECT_NAME`` para usar em e-mail.

    Ex.: ``"Noclaf"`` → ``"noclaf"`` ; ``"Minha API"`` → ``"minhaapi"``.
    Cai para ``"projeto"`` se ``PROJECT_NAME`` não existir.
    """
    name = getattr(settings, "PROJECT_NAME", "") or "projeto"
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    return slug or "projeto"


class Command(BaseCommand):
    help = "Cria usuários de demonstração (Django superuser + admin API + user)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite executar mesmo com DEBUG=False (use por sua conta e risco).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_demo está bloqueado fora de DEBUG. Use --force se realmente quiser."
            )

        # 1) Django superuser — entra em /admin/ com senha em texto puro.
        self._upsert(
            email="admin@admin.com",
            human_password="admin",  # noqa: S106 - seed de demo
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            apply_md5=False,
        )

        # 2) Admin da API — login via API com MD5↑ (front Noclaf).
        slug = project_slug()
        self._upsert(
            email=f"admin@{slug}.com",
            human_password="admin",  # noqa: S106 - seed de demo
            role=User.Role.ADMIN,
            is_staff=False,
            is_superuser=False,
            apply_md5=True,
        )

        # 3) Usuário comum da API.
        self._upsert(
            email="a@a.com",
            human_password="a",  # noqa: S106 - seed de demo
            role=User.Role.USER,
            is_staff=False,
            is_superuser=False,
            apply_md5=True,
        )

        self.stdout.write(self.style.SUCCESS("seed_demo OK."))

    def _upsert(self, *, email, human_password, role, is_staff, is_superuser, apply_md5):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "role": role,
                "is_staff": is_staff,
                "is_active": True,
                "email_verified": True,
            },
        )
        # Garante o estado esperado mesmo se o user já existia.
        user.role = role
        user.is_staff = is_staff
        user.is_active = True
        user.email_verified = True
        # AbstractBaseUser do projeto não tem ``is_superuser`` por padrão —
        # só seta se o atributo existir (compat com possíveis customizações).
        if hasattr(user, "is_superuser"):
            user.is_superuser = is_superuser

        password_for_django = md5_upper(human_password) if apply_md5 else human_password
        user.set_password(password_for_django)
        user.save()

        flow = "MD5↑(front)" if apply_md5 else "texto puro (Django Admin)"
        action = "created" if created else "updated"
        self.stdout.write(f"  - {email} ({role}) {action} — senha '{human_password}' via {flow}")
