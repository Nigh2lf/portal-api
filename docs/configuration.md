# Configuration

Todas as variáveis de ambiente lidas pelo boilerplate. As que **não** têm default precisam estar no seu `.env` antes de subir.

## Core

| Var | Default | Descrição |
|---|---|---|
| `SECRET_KEY` | — (obrigatória) | Chave Django. Em prod, **nunca** commitar. |
| `DEBUG` | `False` | `True` apenas em dev. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` (se DEBUG) | Lista CSV. Em prod **deve** ser explícita. |
| `PROJECT_NAME` | `Project` | Aparece no Django Admin, no Swagger e nos e-mails. Fonte única. |

## Banco de dados

| Var | Default | Descrição |
|---|---|---|
| `DB_ENGINE` | `django.db.backends.mysql` | Use `django.db.backends.sqlite3` em dev. |
| `DB_NAME` | — | Nome do banco (ou caminho do arquivo SQLite). |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | — | Necessários para MySQL. |

## CORS / CSRF

| Var | Default | Descrição |
|---|---|---|
| `CORS_ALLOW_ALL_ORIGINS` | `DEBUG` | **Nunca** ligar em prod. |
| `CORS_ALLOWED_ORIGINS` | `[]` | Lista CSV das origens do front. |
| `CORS_ALLOW_CREDENTIALS` | `False` | Necessário se usa cookies cross-origin. |
| `CSRF_TRUSTED_ORIGINS` | `[]` | Lista CSV (com esquema). |

## JWT (SimpleJWT)

| Var | Default | Descrição |
|---|---|---|
| `JWT_ACCESS_MINUTES` | `60` | Vida do access token. |
| `JWT_REFRESH_MINUTES` | `1440` | Vida do refresh token (1 dia). |

Tokens são rotacionados (`ROTATE_REFRESH_TOKENS=True`) e antigos vão para o blacklist.

## Throttle (rate limit)

| Var | Default | Descrição |
|---|---|---|
| `THROTTLE_ANON` | `100/min` | Sem autenticação. |
| `THROTTLE_USER` | `5000/hour` | Autenticado. |
| `THROTTLE_LOGIN` | `15/min` | Endpoint de login. |
| `THROTTLE_FORGOT` | `5/hour` | Forgot password + send verification. |
| `THROTTLE_CEP` | `60/hour` | Endpoint público de CEP. |

## Forgot password

| Var | Obrigatória? | Descrição |
|---|---|---|
| `URL_FORGOT_PASSWORD` | Sim (se for usar reset) | URL absoluta do front que recebe `?email=&hash=`. |

## API Noclaf (e-mails + CEP)

Configuração unificada — uma chave atende todos os serviços.

| Var | Default | Descrição |
|---|---|---|
| `NOCLAF_API_BASE_URL` | `https://emails.noclaf.com.br/core/` | Base de TODAS as APIs. |
| `NOCLAF_API_KEY` | — | UUID do `X-Api-Key`. **Obrigatório**. |
| `NOCLAF_API_TIMEOUT` | `10` | Timeout em segundos. |

## E-mails (templates / branding)

| Var | Default | Descrição |
|---|---|---|
| `EMAIL_SENDER_NAME` | `PROJECT_NAME` | Nome exibido como remetente. |
| `EMAIL_SENDER_ADDRESS` | `no-reply@example.com` | E-mail do remetente. |
| `EMAIL_LOGO_URL` | `""` | Logo pública (fallback se não houver `PublicAsset`). |
| `EMAIL_BRAND_NAME` | `EMAIL_SENDER_NAME` | Nome usado no header dos templates. |
| `EMAIL_PRIMARY_COLOR` | `#111827` | Cor de botões e títulos. |
| `EMAIL_SUPPORT_ADDRESS` | `EMAIL_SENDER_ADDRESS` | E-mail no footer. |

## Verificação de e-mail (opt-in)

| Var | Default | Descrição |
|---|---|---|
| `EMAIL_VERIFICATION_REQUIRED` | `False` | Ativa o fluxo de código por e-mail no cadastro. |
| `EMAIL_VERIFICATION_CODE_TTL_MIN` | `30` | Validade do código (min). |

## MFA no Django Admin (django-otp)

Apps `django_otp`, `django_otp.plugins.otp_totp` e `django_otp.plugins.otp_static` ficam **sempre instalados** (migrations aplicadas com `migrate`). A exigência de TOTP no `/admin/` é um flag.

| Var | Default | Descrição |
|---|---|---|
| `ADMIN_MFA_ENABLED` | `False` | Quando `True`, `/admin/` vira `OTPAdminSite` e exige TOTP/static token além de usuário/senha. |

Fluxo recomendado:

1. Com `ADMIN_MFA_ENABLED=False`, logue em `/admin/` e cadastre um TOTP em `/admin/otp_totp/totpdevice/add/` (deixe **Confirmed** marcado e escaneie o QR Code no app autenticador).
2. (Recomendado) gere um token estático de emergência: `python manage.py addstatictoken <email>`.
3. Troque para `ADMIN_MFA_ENABLED=True` e reinicie. O próximo login no admin passa a exigir o código de 6 dígitos.

## Storage / S3

| Var | Default | Descrição |
|---|---|---|
| `AWS_STORAGE_BUCKET_NAME` | — | Se setada, ativa S3. Senão, usa filesystem. |
| `AWS_S3_REGION_NAME` | `sa-east-1` | |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | — | |
| `AWS_QUERYSTRING_AUTH` | `True` | URL assinada para `MediaStorage` privado. |

> Nenhuma ACL é enviada no upload: o bucket usa "Bucket owner enforced" (ACLs desabilitadas). Acesso público (prefixo `public/`, usado por `PublicAsset`) é controlado por bucket policy. `PublicMediaStorage` apenas desliga a querystring para gerar URL pública direta.

## CSP

`CSP_DEFAULT_SRC`, `CSP_SCRIPT_SRC`, `CSP_STYLE_SRC`, `CSP_IMG_SRC`, `CSP_CONNECT_SRC`, `CSP_FONT_SRC`, `CSP_FRAME_ANCESTORS` — todas listas CSV. Defaults restritivos (`'self'`).

## Documentação OpenAPI

| Var | Default | Descrição |
|---|---|---|
| `API_TITLE` | `PROJECT_NAME` | Título do schema. |
| `API_DESCRIPTION` | `API documentation` | |
| `API_VERSION` | `1.0.0` | |

## i18n

| Var | Default | Descrição |
|---|---|---|
| `LANGUAGE_CODE` | `pt-br` | |
| `TIME_ZONE` | `America/Sao_Paulo` | |

## Helpers internos

- `env_bool("NOME", default=False)` — aceita `1/true/yes/on`.
- `env_list("NOME", default=[])` — split por vírgula com strip.

## Cron (APScheduler)

| Var | Default | Descrição |
|---|---|---|
| `RUN_CRON` | `False` | `True` liga o `BackgroundScheduler` em `CoreConfig.ready()`. Em prod, ligue em **um único** processo. Detalhes em [cron.md](cron.md). |

## Request logging

Middleware `RequestLoggerMiddleware` grava cada request em `LogRequest`.
Detalhes em [request-logging.md](request-logging.md).

| Var | Default | Descrição |
|---|---|---|
| `LOG_REQUESTS_ENABLED` | `True` | Liga/desliga totalmente o middleware. |
| `LOG_REQUESTS_RETENTION_DAYS` | `30` | Dias mantidos antes do cron `purge_old_request_logs` apagar. |
| `LOG_REQUESTS_PURGE_SCHEDULE` | `03:00` | Horário UTC `HH:MM` em que o cron de purge roda. |
| `LOG_REQUESTS_MAX_BODY` | `10000` | Bytes máximos do body parseado; acima disso vira `"<truncated>"`. |
| `LOG_REQUESTS_EXCLUDE_PATHS` | `/admin/,/static/,/media/,/favicon.ico,/api/v1/health,/api/schema,/api/docs,/api/redoc` | Prefixos de URL ignorados pelo log (csv). |

> ⚠️ **Atenção:** `LOG_REQUESTS_ENABLED=True` **sem** `RUN_CRON=true` (ou cron
> externo equivalente) faz a tabela crescer indefinidamente. Em prod, ligue
> o cron em algum processo ou agende `python manage.py shell -c
> "from core.cron.jobs import purge_old_request_logs; purge_old_request_logs()"`
> via crontab/EventBridge.

## Auditoria de mudanças em models

Signals registram CREATE/UPDATE/DELETE em models declarados na tabela
`LogModelChange`. Detalhes em [model-audit.md](model-audit.md).

| Var | Default | Descrição |
|---|---|---|
| `MODEL_AUDIT_ENABLED` | `False` | Liga os signals em `CoreConfig.ready()`. |
| `MODEL_AUDIT_RETENTION_DAYS` | `30` | Dias mantidos antes do cron `purge_old_audit_logs` apagar. |
| `MODEL_AUDIT_PURGE_SCHEDULE` | `03:15` | Horário UTC `HH:MM` em que o cron de purge roda. |
| `MODEL_AUDIT_MODELS` | `core.User` | Csv `app_label.ModelName` dos models auditados. |

> Mesmo aviso vale: ligar `MODEL_AUDIT_ENABLED=True` sem `RUN_CRON=true` (ou
> purge externo) faz a tabela crescer sem limite.
