# Public Plan (planos e tabela de publicidade)

App `public` · **sem login** (`AllowAny`, throttle `public` por IP) · base:
`/api/v1/public/` (rotas em `public/urls.py`, basenames `public-plan` e
`public-ad-placement`)

Consumido pela página "Anunciar" e pelo cadastro do `portal-web`. Toda resposta
usa o envelope `{success, status, message, data, error}`. Nenhum endpoint grava
e nenhum depende do portal (planos e espaços são globais).

| Método | URL | Descrição |
|---|---|---|
| GET | `/api/v1/public/plans/` | Planos ativos, ordenados por `sort_order`, `name` |
| GET | `/api/v1/public/ad-placements/` | Espaços publicitários ativos, ordenados por `code` |

## GET /api/v1/public/plans/

`data[]`: `id`, `slug`, `name`, `monthly_price` (decimal como string, `null` =
"sob consulta"), `property_limit`, `photo_limit`, `featured_limit`,
`has_realtor_page`, `receives_property_requests`, `has_hotsite`,
`is_recommended`, `is_owner_only` (só aparece na escolha "proprietário"),
`sort_order`.

Sem query params e sem erros além do throttle (`429`).

## GET /api/v1/public/ad-placements/

`data[]`: `code` (ex.: `PH1`), `name`, `page` (`HOME` | `SEARCH` |
`PROPERTY`), `kind` (`POPUP` | `HORIZONTAL` | `SIDEBAR`), `width`, `height`
(pixels), `monthly_price` (decimal como string ou `null`), `notes`.

Sem query params e sem erros além do throttle (`429`).
