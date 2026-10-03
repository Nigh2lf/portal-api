# Request logging

Cada request HTTP que entra na API é registrada na tabela `LogRequest`
pelo middleware [core/middleware/request_logger.py](../core/middleware/request_logger.py).

## Para que serve

- Auditoria (quem chamou o quê, quando, com qual IP).
- Debug (re-executar o request via `curl` salvo no log).
- Métricas rápidas (latência por rota, contagem de erros 5xx).

Para volumetria séria (APM/observabilidade real), use Datadog/Sentry/ELK.
Esta tabela é um log "barato" no próprio banco da aplicação.

## Schema

| Campo | Notas |
|---|---|
| `id` | UUID. |
| `timestamp` | Quando a request começou (UTC). |
| `method` | `GET`, `POST`, … |
| `path` | **Apenas** a URL, sem querystring (ex: `/api/v1/users/`). Facilita agregar por rota. |
| `params` | Querystring serializada como JSON (ex: `{"page": "2"}`). |
| `data` | Body JSON (com chaves sensíveis redatadas como `"***"`). |
| `status_code` | Código HTTP da resposta. |
| `execution_time` | Segundos (float). |
| `ip` | `X-Forwarded-For` (primeiro IP) ou `REMOTE_ADDR`. Truncado em 45 chars. |
| `user_agent` | Header `User-Agent`. |
| `curl` | cURL aproximado pra reproduzir o request. |
| `user` | FK opcional para `User` quando a request é autenticada. `NULL` em anônimas (ON DELETE SET NULL). |
| `user_email` | E-mail do usuário no momento da request (snapshot, sobrevive a delete). |
| `created_at` / `updated_at` | Auditoria padrão. |

## Sanitização de PII

O middleware redacta automaticamente valores cujas **chaves** estejam em:

```
password, old_password, new_password, forgot_password_hash,
email_verification_code, token, access, refresh, secret,
authorization, api_key, apikey
```

No header do cURL, `Authorization`, `Cookie` e `X-Api-Key` viram `***`.

Body com tipo `multipart/*` **não** é parseado (uploads não devem entrar na tabela).

## Configuração

Todas opcionais, com default sensato.

| Env | Default | Efeito |
|---|---|---|
| `LOG_REQUESTS_ENABLED` | `True` | Desliga totalmente o middleware. |
| `LOG_REQUESTS_RETENTION_DAYS` | `30` | Dias mantidos antes do cron purgar. |
| `LOG_REQUESTS_PURGE_SCHEDULE` | `03:00` | Horário UTC `HH:MM` em que o cron de purge roda. |
| `LOG_REQUESTS_MAX_BODY` | `10000` | Body maior que isso vira `"<truncated>"`. |
| `LOG_REQUESTS_EXCLUDE_PATHS` | `/admin/,/static/,/media/,/favicon.ico,/api/v1/health,/api/schema,/api/docs,/api/redoc` | Lista CSV de prefixos ignorados. |

## Limpeza automática (cron)

Sem isso a tabela explode. O job `purge_old_request_logs` em
[core/cron/jobs.py](../core/cron/jobs.py) roda diariamente no horário UTC
definido por `LOG_REQUESTS_PURGE_SCHEDULE` (default **03:00**) e deleta tudo
com `created_at < now() - LOG_REQUESTS_RETENTION_DAYS`.

Requer `RUN_CRON=true` (ver [cron.md](cron.md)).

> ⚠️ **`LOG_REQUESTS_ENABLED=True` + `RUN_CRON=False` = tabela crescendo
> pra sempre.** Em prod, garanta uma das opções abaixo:
>
> 1. Ligar `RUN_CRON=true` em pelo menos um worker (recomendado).
> 2. Cron externo (crontab do SO, AWS EventBridge, GitHub Actions agendado)
>    chamando `python manage.py shell -c "from core.cron.jobs import
>    purge_old_request_logs; purge_old_request_logs()"`.
> 3. Desligar `LOG_REQUESTS_ENABLED=False` se você não consome os logs.

Em prod, sem o cron rodando, faça o purge manual:

```bash
python manage.py shell -c "
from datetime import timedelta
from django.utils import timezone
from core.models import LogRequest
cutoff = timezone.now() - timedelta(days=30)
print(LogRequest.objects.filter(created_at__lt=cutoff).delete())
"
```

## Anti-padrões

- ❌ Logar requests de upload (`multipart`) — middleware já pula o body.
- ❌ Aumentar `LOG_REQUESTS_MAX_BODY` para algo absurdo (>100KB) sem motivo.
- ❌ Expor `LogRequest` via API REST — é dado interno, sensível por natureza.
- ❌ Confiar nesta tabela como "fonte de verdade" de auditoria. Use logging
  estruturado para rotas críticas em paralelo.
