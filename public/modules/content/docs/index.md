# Public Content (blog e dicas)

App `public` · **sem login** (`AllowAny`, throttle `public` por IP) · base:
`/api/v1/public/portals/{portal_slug}/` (rotas em `public/urls.py`, basenames
`public-post` e `public-tip`)

Consumido pelo `portal-web` (SSR). Toda resposta usa o envelope
`{success, status, message, data, error}`. Nenhum endpoint grava.

| Método | URL | Descrição |
|---|---|---|
| GET | `.../portals/{portal_slug}/posts/?page=&page_size=` | Posts do blog, paginados |
| GET | `.../portals/{portal_slug}/posts/{slug}/` | Post completo (com `body`) |
| GET | `.../portals/{portal_slug}/tips/` | Dicas ativas |

`portal_slug` inexistente ou inativo → `404`.

## Escopo

- **Posts**: `is_published = true`, `published_at <= agora` (post sem data não
  aparece) e `portal` nulo (global) **ou** igual ao portal da URL. Ordem:
  `-published_at`.
- **Dicas**: `is_active = true` e `portal` nulo **ou** igual ao portal. Ordem:
  `sort_order`, `-published_at`.

## GET .../posts/

Query: `page` (padrão 1), `page_size` (padrão **9**, máx. 100).

`data`: `count`, `total_pages`, `page`, `page_size`, `next`, `previous`
(URLs absolutas ou `null`), `results[]`.

`results[]`: `id`, `slug`, `title`, `excerpt`, `author_name`,
`cover_image_url` (absoluta ou `null`), `published_at`.

Erros: `404` quando `page` está fora do intervalo ou não é número (comportamento
da `StandardPagination`).

## GET .../posts/{slug}/

`data`: os campos do card acima + `body` (HTML) + `portal` (UUID do portal ou
`null` quando o post é global).

Erros: `404` se o post não existe, não está publicado, ainda não chegou em
`published_at` ou pertence a outro portal.

## GET .../tips/

`data[]`: `id`, `title`, `body` (HTML), `sort_order`.
