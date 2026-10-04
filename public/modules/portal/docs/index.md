# Public Portal (site público)

App `public` · **sem login** (`AllowAny`, throttle `public` por IP) · base:
`/api/v1/public/portals/` (rotas em `public/urls.py`)

Consumido pelo `portal-web` (SSR). Toda resposta usa o envelope
`{success, status, message, data, error}`. Nenhum endpoint grava, exceto o
clique em anúncio.

| Método | URL | Descrição |
|---|---|---|
| GET | `/api/v1/public/portals/` | Portais ativos: `[{id, slug, name, domain}]` |
| GET | `/api/v1/public/portals/{slug}/` | Configuração completa do portal |
| GET | `/api/v1/public/portals/by-host/?host=` | Mesma configuração, resolvida pelo host (`domain` ou `extra_domains`, ignorando `www.` e porta); 404 se não casar. É a rota que o site usa para descobrir o portal |
| GET | `/api/v1/public/portals/{slug}/featured-properties/?limit=12` | Imóveis em destaque (completa com os mais recentes) |
| GET | `/api/v1/public/portals/{slug}/top-searches/?limit=15` | Imóveis mais procurados |
| GET | `/api/v1/public/portals/{slug}/top-neighborhoods/?limit=15` | Bairros mais anunciados |
| GET | `/api/v1/public/portals/{slug}/banners/` | Banners ativos do hero (do portal ou globais) |
| GET | `/api/v1/public/portals/{slug}/ads/?page=HOME&kind=POPUP` | Anúncios publicitários vigentes |
| GET | `/api/v1/public/portals/{slug}/ads/{ad_id}/click/` | Registra `AdClick` e devolve `{link_url, open_in_new_tab}` |
| GET | `/api/v1/public/portals/{slug}/catalog/` | Opções do formulário de busca |

`limit` é limitado a 50.

## Escopo dos imóveis

Em todos os blocos valem só imóveis `PUBLISHED`, `is_active`, não excluídos,
de anunciantes `is_published` cujo `portal` é o próprio portal ou um dos
`combined_portals`, e cuja cidade está nas cidades do portal.

## GET /api/v1/public/portals/{slug}/

`data`: `id`, `slug`, `name`, `domain`, `extra_domains[]`, `main_city`
(`{id, name, slug, state_code}`), `cities[]` (idem), `combined_portals[]`
(UUIDs), `show_city_filter`, `email`, `phone`, `whatsapp`, `address`,
`seo_title`, `seo_description`, `seo_keywords`, `about_text`, `facebook_url`,
`instagram_url`, `ga4_measurement_id`, `recaptcha_site_key`, `logo_url`,
`logo_mobile_url`, `og_image_url`, `primary_color`, `secondary_color`,
`realtors_page_slug`, `results_per_page`, `menu_items[]` (`{label, path,
sort_order}`, só ativos), `total_properties`.

## GET .../featured-properties/

`data[]` (card de imóvel): `id`, `reference_code`, `slug`, `title`,
`ad_type` (`NORMAL` | `FEATURED` | `SUPER_FEATURED`; superdestaque vem antes de destaque na ordenação), `property_type_name`, `property_type_slug`, `city_name`,
`city_slug`, `state_code`, `neighborhood_name`, `neighborhood_slug`,
`bedrooms`, `suites`, `bathrooms`, `parking_spaces`, `built_area`,
`total_area`, `sale_price`, `rent_price`, `seasonal_rent_price`,
`cover_photo_url` (miniatura da capa ou a foto externa), `photos_count`,
`features[]` (nomes), `description_excerpt`, `advertiser_name`,
`advertiser_slug` (só quando o anunciante tem hotsite), `advertiser_logo_url`,
`updated_at`.

## GET .../top-searches/

Usa `SearchLog` dos últimos 90 dias agrupado por objetivo + tipo + bairro. Sem
registros, usa as combinações com mais anúncios.

`data[]`: `purpose` (`SALE` | `RENT` | `SEASONAL`), `property_type`
(`{name, slug}`), `city` (`{name, slug, state_code}`), `neighborhood`
(`{name, slug}`), `total`.

## GET .../top-neighborhoods/

`data[]`: `neighborhood` (`{id, name, slug}`), `city` (`{name, slug, state_code}`), `total`.

## GET .../banners/

`data[]`: `id`, `home_image_url`, `inner_image_url`. O front escolhe um ao acaso.

## GET .../ads/

Query: `page` (`HOME` | `SEARCH` | `PROPERTY`), `kind` (`POPUP` | `HORIZONTAL`
| `SIDEBAR`). Só anúncios `is_active` com `starts_at <= agora <= ends_at`.

`data[]`: `id`, `name`, `image_url`, `link_url`, `open_in_new_tab`,
`placement_code`, `placement_page`, `placement_kind`, `starts_at`, `ends_at`.

## GET .../catalog/

`data`: `property_types[]` (`{id, name, slug, is_residential}`), `cities[]`
(`{id, name, slug, state_code}`), `neighborhoods[]` (`{id, name, slug, city,
city_slug, total}` — só bairros com anúncios), `features[]` (`{id, name, slug,
scope}`).
