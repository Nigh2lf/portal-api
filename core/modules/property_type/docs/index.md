# PropertyType (tipo de imóvel)

`view_name`: `property_type` · papéis: `ADMIN` · base: `/api/v1/property-types/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/property-types/` | `READ` |
| POST | `/api/v1/property-types/` | `CREATE` |
| GET | `/api/v1/property-types/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/property-types/{id}/` | `UPDATE` |
| DELETE | `/api/v1/property-types/{id}/` | `DELETE` |
| GET | `/api/v1/property-types/lookup/` | `READ` |

## GET /api/v1/property-types/

Query params: `search` (`name`, `slug`), `is_active`, `is_residential`,
`ordering` (`sort_order`, `name`, `slug`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `is_residential`, `is_active`,
`sort_order`, `created_at`.

## GET /api/v1/property-types/{id}/

`data`: `id`, `name`, `slug`, `import_aliases` (lista de strings),
`mercadolivre_category`, `is_residential`, `is_active`, `sort_order`,
`legacy_id`, `created_at`, `updated_at`.

## POST /api/v1/property-types/

Body: `name` (obrigatório), `slug` (opcional — gerado de `name`; único),
`import_aliases` (lista), `mercadolivre_category`, `is_residential` (`true`),
`is_active` (`true`), `sort_order` (0).

`data`: campos do detalhe (sem `legacy_id`).
Erros: `400` (validação; `error.slug` duplicado), `403`.

## PUT/PATCH /api/v1/property-types/{id}/

Mesmos campos. `slug` vazio é regenerado. `id`, `created_at`, `updated_at`
read-only.

## DELETE /api/v1/property-types/{id}/

Remoção física. Falha se houver imóveis do tipo (`PROTECT`).

## GET /api/v1/property-types/lookup/

Sem paginação, só `is_active=true`. Aceita `search` e `is_residential`.
`data[]`: `key` (id), `value` (`name`).
