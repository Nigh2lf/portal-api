# ScheduledTaskRun (histórico dos jobs do cron)

`view_name`: `scheduled_task_run` · papéis: `ADMIN` · base: `/api/v1/scheduled-task-runs/`

Somente leitura e exclusão (`POST`/`PUT`/`PATCH` → `405`).
`status`: `RUNNING` | `SUCCESS` | `FAILED`.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/scheduled-task-runs/` | `READ` |
| GET | `/api/v1/scheduled-task-runs/{id}/` | `READ` |
| DELETE | `/api/v1/scheduled-task-runs/{id}/` | `DELETE` |

## GET /api/v1/scheduled-task-runs/

Query params: `search` (`name`, `details`), `name` (exato), `status`,
`started_at__gte`, `started_at__lte` (datetime ISO), `ordering` (`name`,
`status`, `started_at`, `finished_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `status`, `started_at`, `finished_at` (ou
`null`), `created_at`.

## GET /api/v1/scheduled-task-runs/{id}/

`data`: campos da listagem + `details`, `legacy_id`, `updated_at`.

## DELETE /api/v1/scheduled-task-runs/{id}/

Remoção física. Resposta `204`.
