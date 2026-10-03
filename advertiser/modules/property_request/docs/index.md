# Property request (encomendas de parceiros)

`view_name`: `advertiser_property_request` · papéis: `USER`, `ADMIN` (perfil
`ANUNCIANTE`, `view_read`) · base: `/api/v1/advertiser/property-requests/` ·
somente leitura

Toda resposta usa o envelope `{success, status, message, data, error}`.
Usuário sem anunciante: `404` "Usuário sem cadastro de anunciante.".

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/property-requests/` | `READ` |
| GET | `/api/v1/advertiser/property-requests/{id}/` | `READ` |

## GET /api/v1/advertiser/property-requests/

Encomendas "parceiro" (`is_partner_broadcast = true`) do portal do anunciante.
Se o anunciante não tem `receives_property_requests`, a lista vem vazia
(`count = 0`).

Query params: `purpose` (`SALE` | `RENT` | `SEASONAL`), `created_at__gte`,
`created_at__lte`, `search` (`name`, `email`, `phone`, `message`), `ordering`
(`name`, `created_at`; default `-created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `email`, `phone`, `purpose`,
`property_type_name`, `city_name`, `neighborhood_name` (`null` quando não
informados), `min_price`, `max_price`, `is_in_condominium` (`true` | `false` |
`null`), `funding` (`FINANCING` | `CASH` | `FGTS` | `EXCHANGE` | `null`),
`message`, `created_at`.

## GET /api/v1/advertiser/property-requests/{id}/

`data`: mesmo objeto da listagem; `404` fora do escopo acima.
