# Public Property (busca, detalhe, favoritos, eventos)

App `public` · **sem login** (`AllowAny`, throttle `public`) · base:
`/api/v1/public/portals/{portal_slug}/properties/`

Todos os endpoints respeitam o escopo de visibilidade do portal (ver
`public/services/scope.py`): imóveis publicados e ativos de anunciantes
publicados no portal (ou combinados), nas cidades cobertas.

| Método | URL | Descrição |
|---|---|---|
| GET | `.../properties/` | Busca com filtros e paginação |
| GET | `.../properties/{slug}/` | Detalhe (aceita o `reference_code` no lugar do slug) |
| GET | `.../properties/by-ids/?ids=a,b,c` | Cards dos ids informados (favoritos), até 100 |
| POST | `.../properties/inquiries/` | Mensagem ao anunciante do imóvel |
| POST | `.../properties/contact-clicks/` | Clique em telefone/WhatsApp |

## GET .../properties/

Query params: `purpose` (`SALE` padrão, `RENT`, `SEASONAL`), `property_type`,
`city`, `neighborhood`, `advertiser` (slugs), `condominium` (`inside` |
`outside`), `bedrooms` (`1,2,3,4`; 4 = quatro ou mais), `parking` (1–5
exato; 6 = seis ou mais), `price_min`, `price_max` (no preço do objetivo),
`code` (contém), `ordering` (`recent` padrão, `price_asc`, `price_desc`),
`page`, `page_size` (padrão `results_per_page` do portal, máx. 60),
`track=0` para não registrar a busca em `SearchLog`.

Ordenação sempre começa por destaque e por ter foto, como no legado.

`data`: `results[]` (card de imóvel, ver `public/modules/portal/docs`),
`count`, `page`, `page_size`, `total_pages`, `counters` (`{sale, rent,
seasonal}` ignorando o objetivo e o preço), `max_price` (maior preço do
objetivo no conjunto filtrado, para o slider), `applied` (`{property_type,
city, neighborhood}` resolvidos, ou `null`).

Erros `400` em `purpose`, `condominium`, `ordering`, `page`, `page_size`,
`parking`, `price_min`, `price_max`.

## GET .../properties/{slug}/

Registra `PropertyView` (salvo `?track=0`).

`data.property`: `id`, `reference_code`, `slug`, `title`, `ad_type` (`NORMAL` | `FEATURED` | `SUPER_FEATURED`; superdestaque vem antes de destaque na ordenação),
`property_type` (`{id, name, slug}`), `city` (`{id, name, slug, state_code}`),
`neighborhood` (`{id, name, slug}` ou `null`), `neighborhood_name`,
`state_code`, `is_in_condominium`, `bedrooms`, `suites`, `bathrooms`,
`parking_spaces`, `built_area`, `total_area`, `description` (HTML),
`features[]`, `condominium_features[]`, `fees[]` (`{description, amount,
period, notes}`), `sale_price`, `rent_price`, `seasonal_rent_price`,
`photos[]` (`{id, url, thumbnail_url, sort_order, is_cover}`), `advertiser`
(`{id, slug, type, name, creci, logo_url, phone, phone_secondary, whatsapp,
email, website, address, has_hotsite, hotsite_slug, total_properties,
total_sale, total_rent, total_seasonal}`), `published_at`, `created_at`,
`updated_at`.

`data.related[]`: até 6 cards do mesmo tipo e cidade, preço mais próximo.
`data.related_links[]`: `{purpose, property_type, city, neighborhood|null}`.

## POST .../properties/inquiries/

Body: `property` (UUID), `name`, `email`, `phone`, `message`,
`contact_preferences[]` (`WHATSAPP` | `PHONE` | `EMAIL`), `recaptcha_token`
(opcional; validação server-side pendente).

Bloqueia (`403`) remetentes em `BlockedSender` (e-mail ou IP). Resposta
`201` com `data.id`. O envio de e-mail ao anunciante ainda não está ligado.

## POST .../properties/contact-clicks/

Body: `property` (UUID) ou `advertiser` (UUID), `channel` (`PHONE` |
`WHATSAPP`). Resposta `{ok: true}`.

# Public Advertiser (imobiliárias)

Base: `/api/v1/public/portals/{portal_slug}/advertisers/`

| Método | URL | Descrição |
|---|---|---|
| GET | `.../advertisers/` | `{agencies: [...], brokers: [...]}` com página no portal, ordem aleatória |
| GET | `.../advertisers/{slug}/` | Hotsite (exige `has_hotsite`); 404 caso contrário |

Campos: os mesmos de `data.property.advertiser` acima. Para listar os
imóveis do hotsite use a busca com `advertiser={slug}`.

## GET /api/v1/public/portals/{portal_slug}/properties/{slug}/related/

Imóveis relacionados (mesmo tipo e cidade, preço mais próximo no mesmo
objetivo), até 6. Aceita slug ou código. `data`: lista de cards (mesmo formato
de `featured-properties`). `404` se o imóvel não estiver visível no portal.

O detalhe aceita `?related=0` para não calcular os relacionados; o site usa
essa opção e busca esta rota à parte, para a página aparecer antes.
