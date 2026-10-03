# Testing & Quality

## Rodar testes

O projeto usa **pytest** + **pytest-django** + **pytest-mock**.

```bash
pytest core
```

São 44 testes em [core/tests/](../core/tests/), divididos por tema:

| Arquivo | Cobre |
|---|---|
| [test_health.py](../core/tests/test_health.py) | `GET /health/`, acesso ao `/schema/`, envelope em respostas não autenticadas. |
| [test_users.py](../core/tests/test_users.py) | `User`: normalização de email, `set_password` limpa token, soft delete, verificação de e-mail. |
| [test_passwords.py](../core/tests/test_passwords.py) | Validators de senha do Django: aceita forte, rejeita fraca. |
| [test_emails.py](../core/tests/test_emails.py) | Cliente Noclaf é no-op sem `NOCLAF_API_KEY`. |
| [test_cep.py](../core/tests/test_cep.py) | `normalize_cep`, `lookup_cep` (400/503), endpoint `/cep/<cep>/`. |
| [test_permissions.py](../core/tests/test_permissions.py) | Auditoria do router, `SafeDefaultPermission` (parametrizado), `CustomPermissionClass` (`view_name`, `router_user`, `view_read`). |
| [test_checks.py](../core/tests/test_checks.py) | Production hardening, `AllowAny` justificado (W006), PII em serializers (W007/W008), migrations pendentes (E008). |
| [test_admin.py](../core/tests/test_admin.py) | Auto-admin registra todos os models e respeita admins manuais. |
| [conftest.py](../core/tests/conftest.py) | Fixtures `api_client`, `user`, `admin_user`. |

Para rodar isolado:

```bash
pytest core/tests/test_cep.py
pytest core -k "cep"
pytest core -k "permission"
```

Configuração do pytest em [pyproject.toml](../pyproject.toml) (`[tool.pytest.ini_options]`).
Settings de teste usam SQLite in-memory automaticamente quando `DB_NAME=:memory:`.

## Lint / format

```bash
ruff check .
ruff format .
```

Configuração em [pyproject.toml](../pyproject.toml). Regras seguem o padrão `ruff` (pycodestyle + pyflakes + isort).

## Setup de dev

```bash
pip install -r requirements-dev.txt
```

Inclui `pytest`, `pytest-django`, `pytest-mock`, `ruff` + tudo que `requirements.txt` traz.

## Sanity check completo (CI / pré-PR)

Replica o que rodamos antes de cada release:

```bash
python -m venv venv-check && source venv-check/bin/activate
pip install -q -r requirements-dev.txt

SECRET_KEY=t \
DEBUG=True \
DB_ENGINE=django.db.backends.sqlite3 \
DB_NAME=:memory: \
ALLOWED_HOSTS=* \
URL_FORGOT_PASSWORD=https://example.com/reset \
PROJECT_NAME=Noclaf \
pytest core

ruff check .
deactivate && rm -rf venv-check
```

## Boas práticas ao adicionar testes

- Prefira **funções pytest** + fixtures em vez de `TestCase`. Mais conciso.
- Se o teste toca o banco, marque com `@pytest.mark.django_db`. Sem isso o
  pytest-django bloqueia o acesso (`RuntimeError: Database access not allowed`).
- Use a fixture `settings` do pytest-django no lugar de `override_settings`:
  ```python
  def test_x(settings):
      settings.NOCLAF_API_KEY = ""
      ...
  ```
- Para mockar, use `mocker` (pytest-mock):
  ```python
  def test_envia_email(mocker):
      mock = mocker.patch("core.services.services_emails._noclaf_send", return_value=True)
      ...
      mock.assert_called_once()
  ```
- Casos repetitivos viram `@pytest.mark.parametrize`:
  ```python
  @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
  def test_safe_methods(method): ...
  ```
- Reutilize fixtures globais ([conftest.py](../core/tests/conftest.py)): `client`, `api_client`, `user`, `admin_user`.
- Para testes de endpoint protegido: `api_client.force_authenticate(user=user)`.
- Não bater em rede real. Mock `urllib.request.urlopen` ou o helper `_noclaf_send`.
- Para soft delete, sempre verificar `deleted_at`/`is_active`, não `Model.DoesNotExist`.
