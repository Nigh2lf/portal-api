# Portal menu item (menu do site)

`view_name`: `portal_menu_item` · papéis: `ADMIN` · base: `/api/v1/portal-menu-items/`

Itens do menu principal de cada portal. O site público lê os itens ativos
ordenados por `sort_order` em `GET /api/v1/public/portals/{slug}/` (`menu_items`).

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/portal-menu-items/` | `READ` |
| POST | `/api/v1/portal-menu-items/` | `CREATE` |
| GET | `/api/v1/portal-menu-items/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/portal-menu-items/{id}/` | `UPDATE` |
| DELETE | `/api/v1/portal-menu-items/{id}/` | `DELETE` |
| POST | `/api/v1/portal-menu-items/reorder/` | `CREATE` |

## GET /api/v1/portal-menu-items/

Query params: `search` (`label`, `path`), `portal` (UUID), `is_active`,
`ordering` (`sort_order`, `label`, `updated_at`), `page`, `page_size`.

`data.results[]`: `id`, `portal`, `portal_name`, `portal_slug`, `label`,
`path`, `sort_order`, `is_active`, `updated_at`.

## GET /api/v1/portal-menu-items/{id}/

`data`: `id`, `portal`, `portal_name`, `label`, `path`, `sort_order`,
`is_active`, `created_at`, `updated_at`.

## POST / PUT / PATCH

Body: `portal` (UUID, obrigatório), `label` (até 60), `path` (começa com `/`
ou é URL completa), `sort_order` (inteiro, default 0), `is_active` (default
`true`).

Erros: `400` em `error.path` quando o caminho não começa com `/` nem é URL.

## POST /api/v1/portal-menu-items/reorder/

Body: `{"ids": ["<uuid>", ...]}` com todos os itens de **um** portal na ordem
desejada. Grava `sort_order` = posição na lista.

`data[]`: itens do portal na nova ordem (mesmos campos da listagem).
Erros: `400` em `error.ids` (lista vazia, id inexistente ou itens de portais
diferentes).

## Seed

`python manage.py seed_menus` cria o menu padrão do site atual (Início,
Imóveis, Favoritos, Imobiliárias, Planos, Blog, Contato) em todo portal que
ainda não tem itens. Idempotente; `--force` recria mesmo onde já existe.
