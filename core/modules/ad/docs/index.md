# Ad (anúncio publicitário)

`view_name`: `ad` · papéis: `ADMIN` · base: `/api/v1/ads/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/ads/` | `READ` |
| POST | `/api/v1/ads/` | `CREATE` |
| GET | `/api/v1/ads/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/ads/{id}/` | `UPDATE` |
| DELETE | `/api/v1/ads/{id}/` | `DELETE` |

## GET /api/v1/ads/

Query params: `search` (`name`, `link_url`, `portal__name`), `portal` (UUID),
`placement` (UUID), `is_active`, `ordering` (`name`, `starts_at`, `ends_at`,
`is_active`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `portal` (UUID), `portal_name`, `placement`
(UUID), `placement_code`, `placement_name`, `image_url`, `starts_at`,
`ends_at`, `is_active`, `created_at`.

## GET /api/v1/ads/{id}/

`data`: campos da listagem + `link_url`, `open_in_new_tab`, `legacy_id`,
`updated_at`.

## POST /api/v1/ads/

`multipart/form-data`. Obrigatórios: `portal` (UUID), `placement` (UUID),
`name`, `image` (arquivo), `starts_at`, `ends_at` (datetime; `ends_at` não pode
ser anterior a `starts_at`). Opcionais: `link_url`, `open_in_new_tab`
(`false`), `is_active` (`true`).

`data`: `id`, `portal`, `placement`, `name`, `image_url`, `link_url`,
`open_in_new_tab`, `starts_at`, `ends_at`, `is_active`, `created_at`,
`updated_at`.
Erros: `400` (validação; `error.ends_at` quando anterior a `starts_at`), `403`.

## PUT/PATCH /api/v1/ads/{id}/

Mesmos campos; `image` opcional no PATCH. `id`, `created_at`, `updated_at`
read-only.

## DELETE /api/v1/ads/{id}/

Remoção física em cascata das impressões/cliques do anúncio.
