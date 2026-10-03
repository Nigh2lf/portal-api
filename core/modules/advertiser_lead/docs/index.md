# AdvertiserLead (interessado em anunciar)

`view_name`: `advertiser_lead` · papéis: `ADMIN` · base: `/api/v1/advertiser-leads/`

Somente leitura e exclusão (`POST`/`PUT`/`PATCH` → `405`).

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser-leads/` | `READ` |
| GET | `/api/v1/advertiser-leads/{id}/` | `READ` |
| DELETE | `/api/v1/advertiser-leads/{id}/` | `DELETE` |

## GET /api/v1/advertiser-leads/

Query params: `search` (`name`, `email`, `phone`, `company`, `message`),
`portal` (UUID), `created_at__gte`, `created_at__lte` (datetime ISO),
`ordering` (`name`, `email`, `company`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `email`, `phone`, `company`, `portal` (UUID),
`portal_name`, `created_at`.

## GET /api/v1/advertiser-leads/{id}/

`data`: campos da listagem + `message`, `legacy_id`, `updated_at`.

## DELETE /api/v1/advertiser-leads/{id}/

Remoção física. Resposta `204`.
