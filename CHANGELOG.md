# Changelog

Todas as mudanças relevantes deste boilerplate são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
o versionamento segue [SemVer](https://semver.org/lang/pt-BR/) — `MAJOR.MINOR.PATCH`.

> A versão atual é exposta em código por `core.__version__` (ver
> [core/__init__.py](core/__init__.py)) e em [pyproject.toml](pyproject.toml).
> Mantenha as duas em sincronia ao bumpar a versão.

Para projetos derivados: registre no `README` ou em um `BOILERPLATE_VERSION`
de qual versão deste boilerplate vocês saíram.

## [Unreleased]

### Adicionado
- MFA opcional no Django Admin via `django-otp` (`ADMIN_MFA_ENABLED`). Apps
  `django_otp`, `otp_totp` e `otp_static` ficam sempre instalados; o
  `OTPAdminSite` é ativado apenas quando o flag está `True`. Detalhes em
  [docs/auth-permissions.md](docs/auth-permissions.md#mfa-no-django-admin).
- Paginação padrão `core.classes.pagination.StandardPagination` com `page_size`
  via query param e envelope amigável (`count`, `total_pages`, `page`,
  `page_size`, `next`, `previous`, `results`).
- Filtros padrão habilitados: `DjangoFilterBackend`, `SearchFilter`,
  `OrderingFilter`. Basta declarar `filterset_fields` / `search_fields` /
  `ordering_fields` no ViewSet.
- Versionamento explícito da API via `URLPathVersioning`. Default `v1`,
  versões permitidas configuráveis por env `API_ALLOWED_VERSIONS`.
- Comando `seed_demo` cria três usuários de demonstração (idempotente):
  - `admin@admin.com` / senha `admin` em **texto puro** — superuser do
    Django Admin (`is_staff=True`). Login direto em `/admin/`.
  - `admin@<projeto>.com` / senha `admin` (front envia MD5↑) — admin da
    API, role ADMIN. `<projeto>` derivado de `PROJECT_NAME`.
  - `a@a.com` / senha `a` (front envia MD5↑) — usuário comum da API.
  Usuários da API seguem a convenção Noclaf: o front envia a senha em
  MD5 uppercase e o Django aplica PBKDF2 por cima.

## [0.1.0] - 2026-05-05

### Adicionado
- Auditoria automática `created_by` / `updated_by` via `AbstractModel` +
  `BaseModelViewSet`.
- Log de requests HTTP (`LogRequest` + `RequestLoggerMiddleware`) com redação
  de PII e snapshot de usuário.
- Auditoria de mudanças em models (`LogModelChange` + `signals_audit` +
  `CurrentUserMiddleware`).
- Cron com schedules configuráveis (`LOG_REQUESTS_PURGE_SCHEDULE`,
  `MODEL_AUDIT_PURGE_SCHEDULE`).
- Bases abstratas e tabelas de infra concentradas em `core/models_base.py`.

### Mudou
- `models.py` reorganizado em 3 seções (Identidade, RBAC, Conteúdo público).
  Bases e tabelas de log saíram daqui.

### Removido
- Código morto: `SIB_API_KEY`, `permission_type_user.py`,
  `ChangePasswordSerializer`.

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0
