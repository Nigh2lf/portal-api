# Banner

`view_name`: `banner` · papéis: `ADMIN` · base: `/api/v1/banners/`

Imagens de fundo do hero da home (`home_image`) e do topo das páginas internas
(`inner_image`). `portal` nulo = vale para todos os portais.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/banners/` | `READ` |
| POST | `/api/v1/banners/` | `CREATE` |
| GET | `/api/v1/banners/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/banners/{id}/` | `UPDATE` |
| DELETE | `/api/v1/banners/{id}/` | `DELETE` |

## GET /api/v1/banners/

Query params: `search` (`portal__name`), `portal` (UUID), `is_active`,
`ordering` (`created_at`, `is_active`), `page`, `page_size`.

`data.results[]`: `id`, `portal` (UUID ou `null`), `portal_name` (ou `null`),
`home_image_url`, `inner_image_url` (ou `null`), `is_active`, `created_at`.

## GET /api/v1/banners/{id}/

`data`: campos da listagem + `updated_at`.

## POST /api/v1/banners/

`multipart/form-data`. Body: `home_image` (arquivo, obrigatório),
`inner_image` (arquivo, opcional), `portal` (UUID, opcional), `is_active`
(default `true`).

`data`: `id`, `portal`, `home_image_url`, `inner_image_url`, `is_active`,
`created_at`, `updated_at`.
Erros: `400` (validação), `403`.

## PUT/PATCH /api/v1/banners/{id}/

Mesmos campos. `inner_image: null` remove a imagem interna.

## DELETE /api/v1/banners/{id}/

Remoção física do registro (o arquivo no storage não é apagado).
