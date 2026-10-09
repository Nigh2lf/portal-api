# Cron (APScheduler)

Jobs em background dentro do mesmo processo Django, usando
[APScheduler](https://apscheduler.readthedocs.io/) `BackgroundScheduler`.

## Quando usar

- Tarefas pequenas e idempotentes (limpeza, refresh de cache, lembretes).
- Frequências de minutos/horas, não milissegundos.

Para fila distribuída ou jobs longos prefira Celery/RQ.

## Estrutura

```
core/cron/
├── __init__.py        # vazio (não importa nada para evitar custo no boot)
├── jobs.py            # funções dos jobs
└── scheduler.py       # bootstrap do BackgroundScheduler + add_job()
```

## Como funciona

1. [core/apps.py](../core/apps.py) lê `RUN_CRON` em `CoreConfig.ready()`.
2. Se `RUN_CRON=true`, importa [core/cron/scheduler.py](../core/cron/scheduler.py) e chama `start()`.
3. `start()` é **idempotente** (não inicia 2x) e registra os jobs declarados.
4. APScheduler dispara cada job na thread em background.

## Variável de ambiente

| Var | Default | Efeito |
|---|---|---|
| `RUN_CRON` | `False` | `True` liga o scheduler quando o app sobe. |

> **Por que não amarrar em `DEBUG`?** Porque `runserver` faz autoreload em
> 2 processos — você quase nunca quer cron em dev. E em prod com múltiplos
> workers gunicorn, ligar em todos = job rodando N vezes. Use `RUN_CRON`
> só onde quer execução única (ver [deploy](#deploy)).

## Adicionar um job novo

**1.** Defina a função em [core/cron/jobs.py](../core/cron/jobs.py):

```python
import logging
logger = logging.getLogger(__name__)

def cart_abandoned() -> None:
    try:
        # sua lógica aqui — sem args, sem return
        ...
    except Exception:
        logger.exception("cart_abandoned falhou")
```

**Regras:**
- Sem argumentos, sem return.
- Capture exceções dentro do job. Uma exception não tratada some
  silenciosamente nos logs do APScheduler.
- Idempotente: se rodar 2x não pode duplicar efeito.

**2.** Registre em [core/cron/scheduler.py](../core/cron/scheduler.py) dentro de `start()`:

```python
from core.cron.jobs import cart_abandoned

scheduler.add_job(
    cart_abandoned,
    trigger="interval",
    minutes=1,
    id="cart_abandoned",
    replace_existing=True,
)
```

`id` + `replace_existing=True` evitam jobs duplicados se `start()` for
chamado mais de uma vez em runtime.

## Triggers comuns

```python
# A cada 5 minutos
scheduler.add_job(fn, "interval", minutes=5, id="x", replace_existing=True)

# Toda terça às 03:00 UTC
scheduler.add_job(fn, "cron", day_of_week="tue", hour=3, id="x",
                  replace_existing=True)

# Uma vez, em data/hora específica
from datetime import datetime
scheduler.add_job(fn, "date", run_date=datetime(2026, 6, 1, 12), id="x")
```

Doc completa: <https://apscheduler.readthedocs.io/en/3.x/userguide.html#choosing-the-right-scheduler-job-store-s-executor-s-and-trigger-s>.

## Timezone

O scheduler é instanciado com `timezone="UTC"` em
[core/cron/scheduler.py](../core/cron/scheduler.py). Triggers `cron` interpretam horário em UTC.
Mude se tiver bom motivo (mas UTC evita bugs de horário de verão).

## Jobs já registrados

| Job | Trigger | O que faz |
|---|---|---|
| `heartbeat` | a cada 60min | Loga `cron heartbeat ok`. Útil pra confirmar que o scheduler tá vivo. |
| `purge_old_request_logs` | diário, `LOG_REQUESTS_PURGE_SCHEDULE` (default 03:00 UTC) | Remove `LogRequest` com mais de `LOG_REQUESTS_RETENTION_DAYS` (default 30) dias. |
| `purge_old_audit_logs` | diário, `MODEL_AUDIT_PURGE_SCHEDULE` (default 03:15 UTC) | Remove `LogModelChange` com mais de `MODEL_AUDIT_RETENTION_DAYS` (default 30) dias. |
| `nightly_xml_import` | diário, `XML_IMPORT_WINDOW_START` (default 01:00 Brasília) | Dispara `manage.py import_xml --window --origin cron` num processo separado e espera (ver [xml_import/README.md](../xml_import/README.md#execução)). |

## Deploy

Em produção com múltiplos workers (gunicorn/uvicorn), **não ligue
`RUN_CRON=true` em todos** — você teria N execuções por job. Padrões:

**Opção A — worker dedicado (recomendado):**
- Container/ECS task só para cron, sem expor HTTP.
- Sobe `python manage.py runserver --noreload` ou um pequeno entrypoint
  que chame `django.setup()` e fique em sleep.
- Variáveis: `RUN_CRON=true` + tudo que o Django precisa.

**Opção B — um worker do app marcado:**
- Roda gunicorn com 1 worker extra que define `RUN_CRON=true`.
- Os outros workers ficam com `RUN_CRON=false` e atendem só HTTP.
- Mais barato, mas frágil se esse worker reiniciar com frequência.

## Smoke test local

```bash
DJANGO_SETTINGS_MODULE=config.settings \
SECRET_KEY=t DEBUG=True \
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: \
ALLOWED_HOSTS=* URL_FORGOT_PASSWORD=https://example.com/reset \
PROJECT_NAME=Noclaf RUN_CRON=true \
python -c "
import django, logging
logging.basicConfig(level=logging.INFO)
django.setup()
import core.cron.scheduler as s
print('jobs:', [(j.id, str(j.trigger)) for j in s._scheduler.get_jobs()])
s._scheduler.shutdown()
"
```

Saída esperada inclui `APScheduler iniciado com N job(s)` e a lista dos jobs.

## Anti-padrões

- ❌ Job com `time.sleep(60)` esperando algo. Use trigger.
- ❌ Job que escreve em arquivo sem lock entre processos.
- ❌ Job que demora minutos. APScheduler é single-threaded por default; um
  job lento atrasa os outros. Para isso, use Celery.
- ❌ Importar models no topo de [core/cron/scheduler.py](../core/cron/scheduler.py).
  Faça import lazy dentro da função do job para evitar `AppRegistryNotReady`.
