# Plan (plano do anunciante)

`view_name`: `plan` · papéis: `ADMIN` · base: `/api/v1/plans/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/plans/` | `READ` |
| POST | `/api/v1/plans/` | `CREATE` |
| GET | `/api/v1/plans/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/plans/{id}/` | `UPDATE` |
| DELETE | `/api/v1/plans/{id}/` | `DELETE` |
| GET | `/api/v1/plans/lookup/` | `READ` |

## GET /api/v1/plans/

Query params: `search` (`name`, `slug`), `is_active`, `is_recommended`,
`is_owner_only`, `ordering` (`sort_order`, `name`, `monthly_price`,
`created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `monthly_price` (decimal ou `null` =
sob consulta), `property_limit`, `photo_limit`, `featured_limit`,
`is_recommended`, `is_active`, `sort_order`, `created_at`.

## GET /api/v1/plans/{id}/

`data`: `id`, `name`, `slug`, `monthly_price`, `property_limit`,
`photo_limit`, `featured_limit`, `has_realtor_page`,
`receives_property_requests`, `has_hotsite`, `is_owner_only`,
`is_recommended`, `is_active`, `sort_order`, `legacy_id`, `created_at`,
`updated_at`.

## POST /api/v1/plans/

Obrigatórios: `name`, `slug` (único), `property_limit`, `photo_limit`.
Opcionais: `monthly_price`, `featured_limit` (0), `has_realtor_page`,
`receives_property_requests`, `has_hotsite`, `is_owner_only`,
`is_recommended`, `is_active` (`true`), `sort_order` (0).

`data`: campos do detalhe (sem `legacy_id`).
Erros: `400` (validação / `slug` duplicado), `403`.

## PUT/PATCH /api/v1/plans/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/plans/{id}/

Remoção física. Falha se houver anunciantes no plano (`PROTECT`).

## GET /api/v1/plans/lookup/

Sem paginação, só `is_active=true`. Aceita `search`.
`data[]`: `key` (id), `value` (`name`).
