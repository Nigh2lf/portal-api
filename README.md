# Boilerplate API Django

API REST Django + DRF pronta para produção. Autenticação JWT, envelope padronizado, integrações Noclaf (e-mail + CEP), storage S3 com assets públicos/privados, soft delete e UUID em todos os models.

## Stack

- **Python 3.10+** · **Django 4.2** · **DRF 3.14**
- **SimpleJWT** com rotação + blacklist
- **drf-spectacular** (Swagger / Redoc)
- **MySQL** (prod) / **SQLite** (dev)
- **AWS S3** opcional (público + privado)
- **Noclaf API** unificada (envio de e-mail + lookup de CEP)

## Subir em 1 minuto

```bash
git clone <repo> && cd boilerplate-api-django
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

cat > .env <<'EOF'
SECRET_KEY=dev-only-change-me
DEBUG=True
ALLOWED_HOSTS=*
PROJECT_NAME=Noclaf
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
URL_FORGOT_PASSWORD=http://localhost:3000/reset
EOF

python manage.py migrate
python manage.py seed_demo        # cria usuários de demo (ver abaixo)
python manage.py runserver
```

> Quer criar manualmente um admin no lugar do seed?
> `python manage.py createuser --email admin@company.com --password 'Admin@12345' --role ADMIN`

### Usuários criados pelo `seed_demo`

Idempotente — só roda com `DEBUG=True` (use `--force` para ignorar).

| E-mail | Senha (humano) | Como logar | Role | Observação |
|---|---|---|---|---|
| `admin@admin.com` | `admin` | `/admin/` (Django) | ADMIN | Superuser, senha em texto puro. |
| `admin@noclaf.com`¹ | `admin` | API (`/api/v1/auth/login/`) | ADMIN | Front envia `MD5("admin").upper()`. |
| `a@a.com` | `a` | API (`/api/v1/auth/login/`) | USER | Front envia `MD5("a").upper()`. |

¹ O domínio vem de `PROJECT_NAME` (slug em lowercase).

Acesse:
- API: http://localhost:8000/api/v1/health/
- Admin: http://localhost:8000/admin/ (use `admin@admin.com` / `admin`)
- Swagger (logado como staff): http://localhost:8000/api/v1/docs/swagger/

## Documentação

A documentação completa está em [`docs/`](docs/README.md). Atalhos:

| Quero... | Vai em |
|---|---|
| Subir o projeto do zero | [docs/getting-started.md](docs/getting-started.md) |
| Lista de **todas** as envs | [docs/configuration.md](docs/configuration.md) |
| Entender pastas, envelope, BaseModelViewSet | [docs/architecture.md](docs/architecture.md) |
| JWT, roles, permissões | [docs/auth-permissions.md](docs/auth-permissions.md) |
| Modelo `User`, criação, soft delete | [docs/users-and-roles.md](docs/users-and-roles.md) |
| Customizar e-mails (templates, logo, dark mode) | [docs/emails.md](docs/emails.md) |
| Verificação de e-mail por código | [docs/email-verification.md](docs/email-verification.md) |
| Endpoint público de CEP | [docs/cep.md](docs/cep.md) |
| Logos/banners públicos (`PublicAsset`) | [docs/public-assets.md](docs/public-assets.md) |
| Comandos `manage.py` | [docs/management-commands.md](docs/management-commands.md) |
| Testes, lint, CI | [docs/testing-and-quality.md](docs/testing-and-quality.md) |
| Deploy em produção | [docs/deploy.md](docs/deploy.md) |

## Convenções

- Tudo sob `/api/v1/`.
- Toda resposta usa o envelope `{success, status, message, data, error}`.
- PKs são **UUID**.
- Integrações externas falham silenciosamente (logam, não quebram fluxo).
- Senhas têm política configurável via env (`PASSWORD_*`).
