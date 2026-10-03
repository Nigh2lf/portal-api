# City (cidade)

`view_name`: `city` · papéis: `ADMIN` · base: `/api/v1/cities/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/cities/` | `READ` |
| POST | `/api/v1/cities/` | `CREATE` |
| GET | `/api/v1/cities/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/cities/{id}/` | `UPDATE` |
| DELETE | `/api/v1/cities/{id}/` | `DELETE` |
| GET | `/api/v1/cities/lookup/` | `READ` |

## GET /api/v1/cities/

Query params: `search` (`name`, `slug`, `state__code`), `state` (UUID),
`is_active` (`true`/`false`), `ordering` (`name`, `slug`, `created_at`,
`state__code`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `state` (UUID), `state_code`,
`state_name`, `is_active`, `created_at`.

## GET /api/v1/cities/{id}/

`data`: `id`, `name`, `slug`, `state`, `state_code`, `state_name`,
`import_aliases` (lista de strings aceitas na importação XML), `is_active`,
`legacy_id`, `created_at`, `updated_at`.

## POST /api/v1/cities/

Body: `state` (UUID, obrigatório), `name` (obrigatório), `slug` (opcional —
gerado a partir de `name` quando ausente; único dentro do estado),
`import_aliases` (lista de strings, opcional), `is_active` (default `true`).

`data`: `id`, `state`, `name`, `slug`, `import_aliases`, `is_active`,
`created_at`, `updated_at`.
Erros: `400` (validação; `error.slug` quando já existe no estado), `403`.

## PUT/PATCH /api/v1/cities/{id}/

Body: `state`, `name`, `slug`, `import_aliases`, `is_active`. Enviar `slug`
vazio regenera a partir do nome. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/cities/{id}/

Remoção física; bairros vinculados são removidos em cascata. Falha se houver
portal com esta cidade como `main_city` ou imóveis vinculados (`PROTECT`).

## GET /api/v1/cities/lookup/

Sem paginação, só `is_active=true`. Aceita `search` e `state` (UUID).
`data[]`: `key` (id), `value` (`name`).
