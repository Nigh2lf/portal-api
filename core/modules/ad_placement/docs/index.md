# AdPlacement (espaço publicitário)

`view_name`: `ad_placement` · papéis: `ADMIN` · base: `/api/v1/ad-placements/`

`page`: `HOME` | `SEARCH` | `PROPERTY`. `kind`: `POPUP` | `HORIZONTAL` | `SIDEBAR`.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/ad-placements/` | `READ` |
| POST | `/api/v1/ad-placements/` | `CREATE` |
| GET | `/api/v1/ad-placements/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/ad-placements/{id}/` | `UPDATE` |
| DELETE | `/api/v1/ad-placements/{id}/` | `DELETE` |
| GET | `/api/v1/ad-placements/lookup/` | `READ` |

## GET /api/v1/ad-placements/

Query params: `search` (`code`, `name`), `page_type` (filtro por página do site: `HOME` | `SEARCH` | `PROPERTY`; o nome difere do campo porque `page` é a paginação), `kind`, `is_active`,
`ordering` (`code`, `name`, `page`, `kind`, `monthly_price`, `created_at`),
`page` (paginação), `page_size`.

`data.results[]`: `id`, `code`, `name`, `page`, `kind`, `width`, `height`,
`monthly_price` (ou `null`), `is_active`, `created_at`.

## GET /api/v1/ad-placements/{id}/

`data`: campos da listagem + `notes`, `legacy_id`, `updated_at`.

## POST /api/v1/ad-placements/

Obrigatórios: `code` (único, até 10 chars; normalizado para maiúsculas, ex.
`PH1`), `name`, `page`, `kind`, `width`, `height`. Opcionais:
`monthly_price`, `notes`, `is_active` (`true`).

`data`: campos do detalhe (sem `legacy_id`).
Erros: `400` (validação / `code` duplicado), `403`.

## PUT/PATCH /api/v1/ad-placements/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/ad-placements/{id}/

Remoção física. Falha se houver anúncios no espaço (`PROTECT`).

## GET /api/v1/ad-placements/lookup/

Sem paginação, só `is_active=true`. Aceita `search`, `page`, `kind`.
`data[]`: `key` (id), `value` (`name`).
