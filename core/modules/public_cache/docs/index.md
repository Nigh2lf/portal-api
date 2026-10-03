# PublicCache (limpeza manual do cache do site)

`view_name`: `public_cache` · papéis: `ADMIN` · base: `/api/v1/public-cache/`

Controla o cache das leituras públicas (app `public/`) e do site (portal-web).
A invalidação automática já acontece quando um dado muda; esta tela é para o
caso pontual. Implementação em `core/services/public_cache.py`.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/public-cache/` | `READ` |
| POST | `/api/v1/public-cache/invalidate/` | `CREATE` |

## GET /api/v1/public-cache/

`data`:

- `enabled` (bool): `PUBLIC_CACHE_ENABLED`.
- `backend` (str): classe do cache de dados (ex.: `LocMemCache`).
- `site_configured` (bool): `SITE_REVALIDATE_URL` preenchida.
- `scopes[]`: `{value, label}`. Valores: `portal`, `home`, `listing`,
  `catalog`, `content`, `advertiser`, `plans`.
- `portals[]`: `{slug, name}` dos portais ativos.
- `history[]` (até 50, mais recente primeiro): `at` (ISO), `origin`
  (`manual` | `batch`), `user`, `portal` (`""` = todos), `scopes` (`[]` =
  todos), `items` (slug/código de imóvel), `site_ok` (bool ou `null` quando o
  site não foi chamado), `site_error`. O histórico fica no cache de versões e
  zera a cada deploy.

## POST /api/v1/public-cache/invalidate/

Body (todos opcionais):

- `portal`: slug do portal. Vazio = todos.
- `scopes`: lista de escopos. Vazia = todos.
- `property_code`: código do imóvel. Quando informado, limpa só o detalhe
  desse imóvel (com `portal`, restringe aos anunciantes do portal) e ignora
  `scopes`.

Combinações: nada informado limpa tudo; só `portal` limpa todos os escopos do
portal; só `scopes` limpa esses escopos em todos os portais.

`data`: `tags` (tags do Next expiradas; vazia ao limpar só um imóvel, que não
fica no cache do site) e `site` (`{ok, status, error}` da chamada ao
portal-web, ou `null` quando não houve chamada).

Erros `400`: `portal` ("Portal não encontrado."), `scopes` (valor inválido),
`property_code` ("Nenhum imóvel com este código.").
