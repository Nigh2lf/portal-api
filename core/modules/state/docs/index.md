# State (UF)

`view_name`: `state` · papéis: `ADMIN` · base: `/api/v1/states/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/states/` | `READ` |
| POST | `/api/v1/states/` | `CREATE` |
| GET | `/api/v1/states/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/states/{id}/` | `UPDATE` |
| DELETE | `/api/v1/states/{id}/` | `DELETE` |
| GET | `/api/v1/states/lookup/` | `READ` |

## GET /api/v1/states/

Query params: `search` (`code`, `name`), `code`, `ordering` (`code`, `name`,
`created_at`), `page`, `page_size`.

`data.results[]`: `id`, `code`, `name`, `created_at`.

## GET /api/v1/states/{id}/

`data`: `id`, `code`, `name`, `created_at`, `updated_at`.

## POST /api/v1/states/

Body: `code` (obrigatório, 2 letras, único; normalizado para maiúsculas),
`name` (obrigatório).

`data`: `id`, `code`, `name`, `created_at`, `updated_at`.
Erros: `400` (validação / `code` duplicado), `403` (sem permissão `CREATE`).

## PUT/PATCH /api/v1/states/{id}/

Body: `code`, `name`. `id`, `created_at` e `updated_at` são read-only.

## DELETE /api/v1/states/{id}/

Remoção física. Falha se houver cidades vinculadas (`on_delete=PROTECT`).

## GET /api/v1/states/lookup/

Sem paginação. Aceita `search` e `code`. `data[]`: `key` (id), `value` (`name`).
