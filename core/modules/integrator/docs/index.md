# Integrator (integrador de XML/CRM)

`view_name`: `integrator` · papéis: `ADMIN` · base: `/api/v1/integrators/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/integrators/` | `READ` |
| POST | `/api/v1/integrators/` | `CREATE` |
| GET | `/api/v1/integrators/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/integrators/{id}/` | `UPDATE` |
| DELETE | `/api/v1/integrators/{id}/` | `DELETE` |
| GET | `/api/v1/integrators/lookup/` | `READ` |

## GET /api/v1/integrators/

Query params: `search` (`name`, `slug`), `is_active`, `ordering` (`name`,
`slug`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `is_active`, `created_at`.

## GET /api/v1/integrators/{id}/

`data`: `id`, `name`, `slug`, `is_active`, `legacy_id`, `created_at`,
`updated_at`.

## POST /api/v1/integrators/

Body: `name` (obrigatório), `slug` (obrigatório, único), `is_active` (default
`true`).

`data`: `id`, `name`, `slug`, `is_active`, `created_at`, `updated_at`.
Erros: `400` (validação / `slug` duplicado), `403`.

## PUT/PATCH /api/v1/integrators/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/integrators/{id}/

Remoção física; integrações de anunciantes ficam com `integrator = null`.

## GET /api/v1/integrators/lookup/

Sem paginação, só `is_active=true`. Aceita `search`.
`data[]`: `key` (id), `value` (`name`).
