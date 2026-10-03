# PropertyInquiry (lead "Fale com o anunciante")

`view_name`: `property_inquiry` · papéis: `ADMIN` · base: `/api/v1/property-inquiries/`

Somente leitura e exclusão: a criação acontece no site público.
`POST`/`PUT`/`PATCH` respondem `405`.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/property-inquiries/` | `READ` |
| GET | `/api/v1/property-inquiries/{id}/` | `READ` |
| DELETE | `/api/v1/property-inquiries/{id}/` | `DELETE` |

## GET /api/v1/property-inquiries/

Query params: `search` (`name`, `email`, `phone`, `property_reference_code`,
`message`), `advertiser` (UUID), `portal` (UUID), `property` (UUID),
`is_mobile`, `created_at__gte`, `created_at__lte` (datetime ISO, ex.
`2026-01-01T00:00:00`), `ordering` (`name`, `email`, `created_at`), `page`,
`page_size`.

`data.results[]`: `id`, `name`, `email`, `phone`, `advertiser` (UUID),
`advertiser_name`, `portal` (UUID), `portal_name`, `property` (UUID ou
`null`), `property_reference_code`, `forwarded_to_crm_at`, `created_at`.

## GET /api/v1/property-inquiries/{id}/

`data`: campos da listagem + `message`, `contact_preferences` (lista, ex.
`["WHATSAPP", "EMAIL"]`), `property_title` (ou `null`), `ip_address`,
`referer`, `is_mobile`, `legacy_id`, `updated_at`.

## DELETE /api/v1/property-inquiries/{id}/

Remoção física. Resposta `204`.
