# PropertyRequest (encomenda de imóvel)

`view_name`: `property_request` · papéis: `ADMIN` · base: `/api/v1/property-requests/`

Somente leitura e exclusão (`POST`/`PUT`/`PATCH` → `405`).
`purpose`: `SALE` | `RENT` | `SEASONAL`. `funding`: `FINANCING` | `CASH` |
`FGTS` | `EXCHANGE` | `""`.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/property-requests/` | `READ` |
| GET | `/api/v1/property-requests/{id}/` | `READ` |
| DELETE | `/api/v1/property-requests/{id}/` | `DELETE` |

## GET /api/v1/property-requests/

Query params: `search` (`name`, `email`, `phone`, `message`), `portal`,
`advertiser`, `property_type`, `city`, `neighborhood` (UUIDs), `purpose`,
`is_partner_broadcast`, `created_at__gte`, `created_at__lte` (datetime ISO),
`ordering` (`name`, `email`, `purpose`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `email`, `phone`, `purpose`, `portal` (UUID),
`portal_name`, `advertiser` (UUID ou `null`), `advertiser_name` (ou `null`),
`property_type` (UUID ou `null`), `property_type_name`, `city` (UUID ou
`null`), `city_name`, `neighborhood` (UUID ou `null`), `neighborhood_name`,
`min_price`, `max_price`, `is_partner_broadcast`, `created_at`.

## GET /api/v1/property-requests/{id}/

`data`: campos da listagem + `funding`, `message`, `is_in_condominium`
(`true`/`false`/`null`), `ip_address`, `legacy_id`, `updated_at`.

## DELETE /api/v1/property-requests/{id}/

Remoção física. Resposta `204`.
