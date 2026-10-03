# Feature (característica do imóvel / condomínio)

`view_name`: `feature` · papéis: `ADMIN` · base: `/api/v1/features/`

`scope`: `PROPERTY` (infra do imóvel) ou `CONDOMINIUM` (infra do condomínio).

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/features/` | `READ` |
| POST | `/api/v1/features/` | `CREATE` |
| GET | `/api/v1/features/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/features/{id}/` | `UPDATE` |
| DELETE | `/api/v1/features/{id}/` | `DELETE` |
| GET | `/api/v1/features/lookup/` | `READ` |

## GET /api/v1/features/

Query params: `search` (`name`, `slug`), `scope`, `is_active`, `ordering`
(`scope`, `sort_order`, `name`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `scope`, `name`, `slug`, `is_active`, `sort_order`,
`created_at`.

## GET /api/v1/features/{id}/

`data`: campos da listagem + `legacy_id`, `updated_at`.

## POST /api/v1/features/

Body: `scope` (obrigatório), `name` (obrigatório), `slug` (opcional — gerado
de `name`; único dentro do `scope`), `is_active` (`true`), `sort_order` (0).

`data`: `id`, `scope`, `name`, `slug`, `is_active`, `sort_order`,
`created_at`, `updated_at`.
Erros: `400` (validação; `error.slug` duplicado no escopo), `403`.

## PUT/PATCH /api/v1/features/{id}/

Mesmos campos. `slug` vazio é regenerado. `id`, `created_at`, `updated_at`
read-only.

## DELETE /api/v1/features/{id}/

Remoção física; o vínculo com imóveis (M2M) é removido junto.

## GET /api/v1/features/lookup/

Sem paginação, só `is_active=true`. Aceita `search` e `scope`.
`data[]`: `key` (id), `value` (`name`).
