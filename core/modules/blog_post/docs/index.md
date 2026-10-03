# BlogPost (post do blog)

`view_name`: `blog_post` · papéis: `ADMIN` · base: `/api/v1/blog-posts/`

`portal` nulo = vale para todos os portais.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/blog-posts/` | `READ` |
| POST | `/api/v1/blog-posts/` | `CREATE` |
| GET | `/api/v1/blog-posts/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/blog-posts/{id}/` | `UPDATE` |
| DELETE | `/api/v1/blog-posts/{id}/` | `DELETE` |

## GET /api/v1/blog-posts/

Query params: `search` (`title`, `slug`, `excerpt`, `author_name`), `portal`
(UUID), `is_published`, `ordering` (`title`, `published_at`, `is_published`,
`created_at`), `page`, `page_size`.

`data.results[]`: `id`, `title`, `slug`, `portal` (UUID ou `null`),
`portal_name` (ou `null`), `author_name`, `cover_image_url`, `is_published`,
`published_at`, `created_at`.

## GET /api/v1/blog-posts/{id}/

`data`: campos da listagem + `excerpt`, `body`, `legacy_id`, `updated_at`.

## POST /api/v1/blog-posts/

Obrigatórios: `title`, `body`. Opcionais: `slug` (gerado de `title` quando
ausente; único), `portal` (UUID), `excerpt`, `author_name`, `cover_image`
(arquivo, multipart), `is_published` (`false`), `published_at`.

`data`: `id`, `portal`, `title`, `slug`, `excerpt`, `body`, `author_name`,
`cover_image_url`, `is_published`, `published_at`, `created_at`, `updated_at`.
Erros: `400` (validação; `error.slug` duplicado), `403`.

## PUT/PATCH /api/v1/blog-posts/{id}/

Mesmos campos. `slug` vazio é regenerado; `cover_image: null` remove a capa.
`id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/blog-posts/{id}/

Remoção física.
