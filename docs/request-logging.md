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
| `LOG_REQUESTS_RETENTION_DAYS` | `30` | Dias mantidos pelo comando `purge_logs`. |
| `LOG_REQUESTS_MAX_BODY` | `10000` | Body maior que isso vira `"<truncated>"`. |
| `LOG_REQUESTS_EXCLUDE_PATHS` | `/admin/,/static/,/media/,/favicon.ico,/api/v1/health,/api/schema,/api/docs,/api/redoc` | Lista CSV de prefixos ignorados. |

## Limpeza

O projeto não tem agendador: sem limpeza a tabela só cresce. O comando
[purge_logs](../core/management/commands/purge_logs.py) apaga tudo com
`created_at < now() - LOG_REQUESTS_RETENTION_DAYS` (e faz o mesmo para
`LogModelChange` e `SearchLog`, cada um com a sua retenção):

```bash
python manage.py purge_logs --dry-run   # só conta
python manage.py purge_logs
```

Rode à mão ou por um agendador externo. Se você não consome os logs, desligue
com `LOG_REQUESTS_ENABLED=False`.

## Anti-padrões

- ❌ Logar requests de upload (`multipart`) — middleware já pula o body.
- ❌ Aumentar `LOG_REQUESTS_MAX_BODY` para algo absurdo (>100KB) sem motivo.
- ❌ Expor `LogRequest` via API REST — é dado interno, sensível por natureza.
- ❌ Confiar nesta tabela como "fonte de verdade" de auditoria. Use logging
  estruturado para rotas críticas em paralelo.
