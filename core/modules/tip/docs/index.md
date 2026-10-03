# Tip (dica)

`view_name`: `tip` · papéis: `ADMIN` · base: `/api/v1/tips/`

`portal` nulo = vale para todos os portais.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/tips/` | `READ` |
| POST | `/api/v1/tips/` | `CREATE` |
| GET | `/api/v1/tips/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/tips/{id}/` | `UPDATE` |
| DELETE | `/api/v1/tips/{id}/` | `DELETE` |

## GET /api/v1/tips/

Query params: `search` (`title`, `body`), `portal` (UUID), `is_active`,
`ordering` (`sort_order`, `title`, `published_at`, `created_at`), `page`,
`page_size`.

`data.results[]`: `id`, `title`, `portal` (UUID ou `null`), `portal_name` (ou
`null`), `is_active`, `published_at`, `sort_order`, `created_at`.

## GET /api/v1/tips/{id}/

`data`: campos da listagem + `body`, `legacy_id`, `updated_at`.

## POST /api/v1/tips/

Obrigatórios: `title`, `body`. Opcionais: `portal` (UUID), `is_active`
(`true`), `published_at`, `sort_order` (0).

`data`: `id`, `portal`, `title`, `body`, `is_active`, `published_at`,
`sort_order`, `created_at`, `updated_at`.
Erros: `400` (validação), `403`.

## PUT/PATCH /api/v1/tips/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/tips/{id}/

Remoção física.
