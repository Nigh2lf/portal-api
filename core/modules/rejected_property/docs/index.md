# RejectedProperty (imóvel rejeitado na moderação)

`view_name`: `rejected_property` · papéis: `ADMIN` · base: `/api/v1/rejected-properties/`

Referências de imóveis do XML barradas pela moderação (a importação pula
estes códigos).

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/rejected-properties/` | `READ` |
| POST | `/api/v1/rejected-properties/` | `CREATE` |
| GET | `/api/v1/rejected-properties/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/rejected-properties/{id}/` | `UPDATE` |
| DELETE | `/api/v1/rejected-properties/{id}/` | `DELETE` |

## GET /api/v1/rejected-properties/

Query params: `search` (`property_reference_code`, `reason`,
`advertiser__name`), `advertiser` (UUID), `ordering`
(`property_reference_code`, `created_at`, `advertiser__name`), `page`,
`page_size`.

`data.results[]`: `id`, `advertiser` (UUID), `advertiser_name`,
`property_reference_code`, `reason`, `created_at`.

## GET /api/v1/rejected-properties/{id}/

`data`: campos da listagem + `updated_at`.

## POST /api/v1/rejected-properties/

Body: `advertiser` (UUID, obrigatório), `property_reference_code`
(obrigatório; único por anunciante), `reason` (opcional).

`data`: `id`, `advertiser`, `property_reference_code`, `reason`, `created_at`,
`updated_at`.
Erros: `400` (validação / par anunciante+referência duplicado), `403`.

## PUT/PATCH /api/v1/rejected-properties/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/rejected-properties/{id}/

Remoção física (libera a referência para a próxima importação).
