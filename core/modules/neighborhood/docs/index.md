# Neighborhood (bairro)

`view_name`: `neighborhood` · papéis: `ADMIN` · base: `/api/v1/neighborhoods/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/neighborhoods/` | `READ` |
| POST | `/api/v1/neighborhoods/` | `CREATE` |
| GET | `/api/v1/neighborhoods/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/neighborhoods/{id}/` | `UPDATE` |
| DELETE | `/api/v1/neighborhoods/{id}/` | `DELETE` |
| GET | `/api/v1/neighborhoods/lookup/` | `READ` |

## GET /api/v1/neighborhoods/

Query params: `search` (`name`, `slug`, `city__name`), `city` (UUID),
`city__state` (UUID), `is_active`, `ordering` (`name`, `slug`, `created_at`,
`city__name`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `city` (UUID), `city_name`,
`state` (UUID), `state_code`, `is_active`, `created_at`.

## GET /api/v1/neighborhoods/{id}/

`data`: `id`, `name`, `slug`, `city`, `city_name`, `state_code`,
`import_aliases` (lista de strings), `is_active`, `legacy_id`, `created_at`,
`updated_at`.

## POST /api/v1/neighborhoods/

Body: `city` (UUID, obrigatório), `name` (obrigatório), `slug` (opcional —
gerado de `name`; único dentro da cidade), `import_aliases` (lista, opcional),
`is_active` (default `true`).

`data`: `id`, `city`, `name`, `slug`, `import_aliases`, `is_active`,
`created_at`, `updated_at`.
Erros: `400` (validação; `error.slug` quando já existe na cidade), `403`.

## PUT/PATCH /api/v1/neighborhoods/{id}/

Body: `city`, `name`, `slug`, `import_aliases`, `is_active`. `slug` vazio é
regenerado. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/neighborhoods/{id}/

Remoção física. Imóveis que apontavam para o bairro ficam com
`neighborhood = null` (`SET_NULL`).

## GET /api/v1/neighborhoods/lookup/

Sem paginação, só `is_active=true`. Aceita `search`, `city` (UUID) e
`city__state` (UUID). `data[]`: `key` (id), `value` (`name`).
