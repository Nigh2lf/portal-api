# Deploy

Checklist de produção. Pegue cada item, marque, suba.

## Variáveis obrigatórias

```bash
SECRET_KEY=<aleatório, 50+ chars, NUNCA reusar de dev>
DEBUG=False
ALLOWED_HOSTS=api.meuapp.com,meuapp.com
PROJECT_NAME=MeuApp
```

## Banco de dados (MySQL)

```bash
DB_ENGINE=django.db.backends.mysql
DB_NAME=meuapp
DB_USER=meuapp
DB_PASSWORD=<secret>
DB_HOST=db.internal
DB_PORT=3306
```

Rode `python manage.py migrate --noinput` no deploy.

## Storage S3

```bash
AWS_STORAGE_BUCKET_NAME=meuapp-media
AWS_S3_REGION_NAME=sa-east-1
AWS_ACCESS_KEY_ID=<secret>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_QUERYSTRING_AUTH=True   # URLs assinadas para arquivos privados
```

Nenhuma ACL é enviada no upload: o bucket usa "Bucket owner enforced" (ACLs desabilitadas). O acesso público do `PublicAsset` (prefixo `public/`) é controlado por bucket policy (ver [public-assets.md](public-assets.md)).

## CORS / CSRF

```bash
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://app.meuapp.com,https://admin.meuapp.com
CORS_ALLOW_CREDENTIALS=True
CSRF_TRUSTED_ORIGINS=https://app.meuapp.com,https://admin.meuapp.com
```

## CSP

Padrão é `'self'`. Se usa CDN, fontes externas, Google Analytics, etc., libere explicitamente:

```bash
CSP_SCRIPT_SRC=self,https://cdn.meuapp.com
CSP_STYLE_SRC=self,https://fonts.googleapis.com
CSP_IMG_SRC=self,data:,https://meuapp-media.s3.sa-east-1.amazonaws.com
CSP_FONT_SRC=self,https://fonts.gstatic.com
CSP_CONNECT_SRC=self,https://api.meuapp.com
CSP_FRAME_ANCESTORS=none
```

## JWT

```bash
JWT_ACCESS_MINUTES=60
JWT_REFRESH_MINUTES=1440
```

Aumente apenas se tiver bom motivo. Lembre que blacklist roda em DB.

## Throttle (ajuste pelo seu tráfego real)

```bash
THROTTLE_ANON=200/min
THROTTLE_USER=10000/hour
THROTTLE_LOGIN=20/min
THROTTLE_FORGOT=5/hour
THROTTLE_CEP=120/hour
```

## E-mail (Brevo) e CEP (ViaCEP)

```bash
BREVO_API_KEY=<chave da Brevo>
# Opcionais (defaults bons):
EMAIL_SENDER_ADDRESS=<remetente validado na Brevo>
CEP_CACHE_DAYS=365
```

## Branding de e-mail

```bash
EMAIL_SENDER_NAME=MeuApp
EMAIL_SENDER_ADDRESS=no-reply@meuapp.com
EMAIL_SUPPORT_ADDRESS=suporte@meuapp.com
EMAIL_BRAND_NAME=MeuApp
EMAIL_PRIMARY_COLOR=#4f46e5
# Logo: prefira cadastrar PublicAsset(name="email_logo") via /admin/
EMAIL_LOGO_URL=https://meuapp-media.s3.sa-east-1.amazonaws.com/public/logo.png
```

## Reset de senha

```bash
URL_FORGOT_PASSWORD=https://app.meuapp.com/reset-senha
```

## Verificação de e-mail (se for usar)

```bash
EMAIL_VERIFICATION_REQUIRED=True
EMAIL_VERIFICATION_CODE_TTL_MIN=30
```

## MFA no Django Admin (recomendado em prod)

```bash
ADMIN_MFA_ENABLED=True
```

Antes de subir com o flag em `True`, garanta que pelo menos um superuser já
tem TOTPDevice **Confirmed** cadastrado (ver [auth-permissions.md](auth-permissions.md#mfa-no-django-admin)). Caso contrário, ninguém entra em `/admin/`.

## Tarefas agendadas

O serviço web não agenda nada (o APScheduler interno foi removido em 2026-10-09
para o processo ficar menor). O que antes era job vira comando, rodado à mão ou
por um agendador externo, como um serviço *Cron Schedule* do Railway no mesmo repo:

- `python manage.py import_xml --window --origin cron`: importação XML da janela noturna.
- `python manage.py purge_logs`: apaga `LogRequest`, `LogModelChange` e `SearchLog` antigos.

## Comandos no deploy

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seedpermissions   # opcional, idempotente
```

## Railway

Configuração em `railway.json` (tem precedência sobre a interface):

- **`preDeployCommand`**: `migrate` e `collectstatic` rodam antes do container
  novo receber tráfego. O `collectstatic` envia os estáticos para o S3 e leva
  mais de um minuto; no `startCommand` ele atrasava o gunicorn e gerava 502
  a cada deploy.
- **`startCommand`**: só o gunicorn.
- **`healthcheckPath`**: `/api/v1/health/`. O Railway só troca o tráfego quando
  o container novo responder 200; o antigo continua no ar até lá. O request
  chega com `Host: healthcheck.railway.app`, incluído no `ALLOWED_HOSTS`
  automaticamente quando `RAILWAY_ENVIRONMENT` existe, e isento do redirect
  para HTTPS (`SECURE_REDIRECT_EXEMPT`).

## Servidor

Use **gunicorn** + **nginx** (ou ALB direto).

```bash
gunicorn config.wsgi:application \
  --workers 4 \
  --threads 2 \
  --timeout 60 \
  --bind 0.0.0.0:8000
```

## Pré-deploy: rodar os checks de segurança

```bash
DEBUG=False \
SECRET_KEY=<real> \
ALLOWED_HOSTS=api.meuapp.com \
BREVO_API_KEY=<real> \
python manage.py check --deploy --fail-level WARNING
```

Se passar, os checks do projeto (`core.E004`–`core.W004`) estão satisfeitos.
Detalhes em [auth-permissions.md](auth-permissions.md#checks-de-hardening-de-produção).

## Checagem rápida pós-deploy

```bash
curl -i https://api.meuapp.com/api/v1/health/
# 200 + envelope { "success": true, ... }
```

Acesse `/admin/`, logue, tente abrir `/api/v1/docs/swagger/` — deve abrir.

## Coisas que **NÃO** podem ir para prod

- `DEBUG=True`
- `CORS_ALLOW_ALL_ORIGINS=True`
- `SECRET_KEY` igual ao do dev
- `ALLOWED_HOSTS=*`
- `BREVO_API_KEY` vazio (e-mails não serão enviados)

## Logs

Tudo via `logging` padrão Django. Configure handler para CloudWatch / Datadog / etc. via `LOGGING` em [config/settings.py](../config/settings.py) se precisar.

Falhas em integrações (Brevo, ViaCEP) **logam mas não levantam**, então monitore o nível `WARNING`/`ERROR` do logger `core.services.*`.
