# Getting Started

Subir o boilerplate do zero, do clone ao primeiro request autenticado.

## 1. Pré-requisitos

- Python **3.10+**.
- MySQL 8 (produção) **ou** SQLite (dev/testes).
- `pip` + `venv`.

## 2. Clone & venv

```bash
git clone <repo>
cd boilerplate-api-django

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt          # produção
pip install -r requirements-dev.txt      # dev (inclui ruff, pytest etc.)
```

## 3. Variáveis de ambiente mínimas

Crie um `.env` na raiz:

```bash
SECRET_KEY="troque-isto-em-prod"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# DB (dev → sqlite local; prod → mysql)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Identidade do projeto
PROJECT_NAME=MeuApp

# Forgot password (URL do front que recebe o token)
URL_FORGOT_PASSWORD=https://app.exemplo.com/reset-password
```

> Lista completa em [configuration.md](configuration.md).

## 4. Migrate

```bash
python manage.py migrate
```

## 5. Criar o primeiro admin

Você tem duas opções.

### Opção A — Seed de demo (mais rápido, só dev)

```bash
python manage.py seed_demo
```

Cria três usuários idempotentes:

| E-mail | Senha (humano) | Logar onde | Role |
|---|---|---|---|
| `admin@admin.com` | `admin` | `/admin/` (Django, texto puro) | ADMIN (superuser) |
| `admin@<projeto>.com`¹ | `admin` | API (`/api/v1/auth/login/`, **MD5↑**) | ADMIN |
| `a@a.com` | `a` | API (`/api/v1/auth/login/`, **MD5↑**) | USER |

¹ `<projeto>` vem de `PROJECT_NAME` (slug minúsculo).

O comando aborta com `DEBUG=False` — passe `--force` se realmente quiser.
Na convenção Noclaf o front envia a senha em **MD5 hex uppercase**, então o
login pela API espera, p.ex., `MD5("admin").upper() = 21232F297A57A5A743894A0E4A801FC3`.

### Opção B — Criar manualmente

```bash
python manage.py createuser --email admin@company.com --password 'Admin@12345' --role ADMIN
```

Vai pedir email + senha (interativo). O usuário criado entra como `role=ADMIN` e `is_staff=True` — pode acessar `/admin/` e qualquer endpoint protegido.

> Detalhes em [management-commands.md](management-commands.md#createuser).

## 6. Subir o servidor

```bash
python manage.py runserver
```

A API responde em `http://localhost:8000/api/v1/`.

## 7. Primeiro request

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"voce@exemplo.com","password":"SuaSenhaForte#1234"}'
```

Resposta (envelope padrão):
```json
{
  "success": true,
  "status": 200,
  "message": "",
  "data": { "access": "eyJ...", "refresh": "eyJ..." },
  "error": null
}
```

Use o `access` no header `Authorization: Bearer eyJ...` para chamar endpoints protegidos.

## 8. Acessar a documentação OpenAPI

Faça login em `http://localhost:8000/admin/` (com o usuário criado no passo 5) e abra:

- Swagger UI → `http://localhost:8000/api/v1/docs/swagger/`
- Redoc → `http://localhost:8000/api/v1/docs/redoc/`

> Os docs **sempre** exigem `is_staff=True`, mesmo em DEBUG. Isso é proposital.

## 9. Testes

```bash
pytest core
```

Esperado: `OK` com todos os testes passando.

## Próximos passos

- [auth-permissions.md](auth-permissions.md) — entender o modelo de permissões.
- [emails.md](emails.md) — configurar a Brevo para enviar e-mails reais.
- [architecture.md](architecture.md) — criar seu primeiro `ViewSet`.
