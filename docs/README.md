# Boilerplate API Django — Documentação

Bem-vindo. Esta pasta contém a documentação completa do boilerplate. Cada arquivo é independente e cobre um tópico específico.

## Índice

| Arquivo | O que tem |
|---|---|
| [getting-started.md](getting-started.md) | Subir o projeto do zero (clone → migrate → primeiro usuário → primeiro request). |
| [configuration.md](configuration.md) | **Todas** as variáveis de ambiente, com defaults e o que cada uma controla. |
| [architecture.md](architecture.md) | Visão geral: pastas, camadas, envelope de resposta, exception handler. |
| [auth-permissions.md](auth-permissions.md) | JWT (login/refresh/logout), o eixo `is_staff` × `role`, classes `IsAdminRole`, `IsUserRole`, `CustomPermissionClass`. |
| [users-and-roles.md](users-and-roles.md) | Modelo `User`, criação via API e via comando, soft delete, profiles & permissions. |
| [emails.md](emails.md) | Classe de serviço Brevo, templates `_base.html` (dark mode, mobile, Outlook), logo via `PublicAsset`. |
| [email-verification.md](email-verification.md) | Fluxo opt-in de confirmação por código (envio + verify). |
| [cep.md](cep.md) | Endpoint público `/api/v1/cep/<cep>/` + service `lookup_cep` (ViaCEP com cache em `PostalCode`). |
| [public-assets.md](public-assets.md) | Imagens públicas vs. privadas (`PublicAsset` × `User.profile_image`). |
| [management-commands.md](management-commands.md) | `createuser`, `createpermission`, `seedpermissions`. |
| [cron.md](cron.md) | Jobs em background com APScheduler (`RUN_CRON`, `core/cron/`). |
| [request-logging.md](request-logging.md) | Middleware que registra cada request em `LogRequest` (com sanitização e purge automático). |
| [model-audit.md](model-audit.md) | Signals que registram CREATE/UPDATE/DELETE em models declarados (`LogModelChange`). |
| [testing-and-quality.md](testing-and-quality.md) | Como rodar testes (pytest + pytest-django + pytest-mock), `ruff`, pre-commit. |
| [deploy.md](deploy.md) | Checklist de produção: S3, CSP, throttle, secrets. |

## Atalhos para usuários novos

- **Quero subir local agora**: [getting-started.md](getting-started.md).
- **Quero entender as envs**: [configuration.md](configuration.md).
- **Quero criar um endpoint novo**: [architecture.md](architecture.md) → seção `BaseModelViewSet`.
- **Quero entender quem pode fazer o quê**: [auth-permissions.md](auth-permissions.md).
- **Quero customizar a marca/logo nos e-mails**: [emails.md](emails.md).

## Convenções

- Endpoints são versionados sob **`/api/v1/`**.
- Toda resposta usa o **envelope** `{success, status, message, data, error}`.
- Models usam **UUID** como PK.
- Senhas seguem políticas configuráveis via env (`PASSWORD_*`).
- Falhas em integrações externas (Brevo, ViaCEP) **nunca** quebram fluxo de negócio — são logadas e suprimidas.
