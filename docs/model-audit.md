# Auditoria de mudanças em models

Sistema opt-in que registra **CREATE / UPDATE / DELETE** em models declarados,
populando a tabela `LogModelChange` via Django signals.

Cobre qualquer caminho que chame `Model.save()` ou `Model.delete()`:

- API (ViewSets do DRF)
- Django Admin
- Management commands (`createuser` etc.)
- Shell (`python manage.py shell`)
- Migrations de dados

## Quando usar

- Compliance / LGPD ("quem editou o quê e quando").
- Debug de mudanças misteriosas em produção.
- Trail mínima para tabelas críticas (usuários, permissões, billing).

Para **observabilidade** completa (eventos de domínio, rastros distribuídos),
use uma ferramenta dedicada (Sentry, Datadog, EventBridge).

## Como ligar

Por padrão **desligado**. Em `.env`:

```dotenv
MODEL_AUDIT_ENABLED=True
MODEL_AUDIT_RETENTION_DAYS=30
MODEL_AUDIT_PURGE_SCHEDULE=03:15
MODEL_AUDIT_MODELS=core.User
```

`MODEL_AUDIT_MODELS` aceita CSV de `app_label.ModelName`. Exemplo:

```dotenv
MODEL_AUDIT_MODELS=core.User,core.PublicAsset,core.Profile
```

A conexão dos signals é feita em `CoreConfig.ready()` — basta subir o app
com a env ligada.

## Schema da tabela `LogModelChange`

| Campo | Notas |
|---|---|
| `id` | UUID. |
| `app_label` / `model_name` | Identifica o tipo de objeto (ex: `core` / `User`). |
| `object_id` | PK do objeto como string (UUID ou int). |
| `action` | `CREATE`, `UPDATE` ou `DELETE`. |
| `changes` | JSON. CREATE: `{"new": {...}}`. UPDATE: `{campo: {old, new}}`. DELETE: `{"snapshot": {...}}`. |
| `actor` | FK para `User` (quem fez a ação) — `NULL` em fluxos sem request (shell, jobs). |
| `actor_email` | Snapshot do e-mail no momento, mantido mesmo se o user for deletado. |
| `created_at` | Quando o evento foi registrado. |

## Captura do `actor`

O middleware [core/middleware/current_user.py](../core/middleware/current_user.py)
guarda `request.user` em um `ContextVar` por request. Os signals leem esse
valor. Em fluxos **sem request**:

- `python manage.py shell` → `actor=None`
- `python manage.py createuser` → `actor=None`
- Cron jobs → `actor=None`

Para anotar manualmente o actor em scripts, use:

```python
from core.middleware.current_user import set_current_user
set_current_user(some_user)
```

## Sanitização de PII

Campos sensíveis **nunca** têm valor gravado — aparecem como `<redacted>` no
JSON. Lista atual em [core/signals_audit.py](../core/signals_audit.py)
(`_SENSITIVE_FIELDS`):

- `password`
- `forgot_password_hash` / `forgot_password_expire`
- `email_verification_code` / `email_verification_expire`

## Soft delete vs hard delete

`User.delete()` é **soft** (chama `save` setando `deleted_at`). Por isso
aparece como `UPDATE` no log, com `is_active` e `deleted_at` no diff —
**não** como `DELETE`. Esse é o comportamento esperado: nenhum registro
foi removido do banco.

Hard delete (`Model.objects.filter(...).delete()` direto, ou `User`
chamado em modelos sem soft delete) gera evento `DELETE` com snapshot
do objeto antes da remoção.

## Limpeza automática (cron)

Sem isso a tabela cresce sem fim. O job `purge_old_audit_logs` em
[core/cron/jobs.py](../core/cron/jobs.py) roda diariamente no horário UTC
definido por `MODEL_AUDIT_PURGE_SCHEDULE` (default **03:15**)
e deleta tudo com `created_at < now() - MODEL_AUDIT_RETENTION_DAYS`.

Requer `RUN_CRON=true` (ver [cron.md](cron.md)).

> ⚠️ **`MODEL_AUDIT_ENABLED=True` + `RUN_CRON=False` = tabela crescendo
> indefinidamente.** Em prod, garanta uma das opções:
>
> 1. `RUN_CRON=true` em pelo menos um worker.
> 2. Cron externo: `python manage.py shell -c "from core.cron.jobs import
>    purge_old_audit_logs; purge_old_audit_logs()"`.
> 3. `MODEL_AUDIT_ENABLED=False` se você não consome os logs.

## Custo

Cada `save()` em model auditado faz **uma query extra** (`pre_save` busca o
estado anterior) e **uma insert** (`post_save` grava o log). Em rotas
quentes (criação em massa) o impacto é perceptível.

Mitigações:

- Audite apenas models críticos.
- Para imports em lote, use `Model.objects.bulk_create` / `bulk_update`
  (que **não** disparam signals — escolha consciente; o lote inteiro fica
  sem log).

## Anti-padrões

- ❌ Auditar tabelas de log/cache (loop ou tráfego enorme).
- ❌ Expor `LogModelChange` via API REST sem autorização forte.
- ❌ Confiar 100% como histórico legal — para compliance jurídico, use
  ferramenta dedicada com assinatura/imutabilidade.
- ❌ Auditar com `MODEL_AUDIT_ENABLED=True` mas sem nenhum mecanismo de
  purge — a tabela explode.
