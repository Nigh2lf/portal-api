# Portal

`view_name`: `portal` · papéis: `ADMIN` · base: `/api/v1/portals/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/portals/` | `READ` |
| POST | `/api/v1/portals/` | `CREATE` |
| GET | `/api/v1/portals/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/portals/{id}/` | `UPDATE` |
| DELETE | `/api/v1/portals/{id}/` | `DELETE` |
| GET | `/api/v1/portals/lookup/` | `READ` |

## GET /api/v1/portals/

Query params: `search` (`name`, `slug`, `domain`), `is_active`, `main_city`
(UUID), `ordering` (`name`, `slug`, `domain`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `domain`, `is_active`, `main_city`
(UUID), `main_city_name`, `email`, `logo_url`, `created_at`.

## GET /api/v1/portals/{id}/

`data`: `id`, `slug`, `name`, `domain`, `extra_domains` (lista de strings),
`is_active`, `main_city`, `main_city_name`, `cities` (lista de UUID de `City`),
`combined_portals` (lista de UUID de `Portal`), `show_city_filter`, `email`,
`phone`, `whatsapp`, `address`, `seo_title`, `seo_description`, `seo_keywords`,
`about_text`, `facebook_url`, `instagram_url`, `ga4_measurement_id`,
`recaptcha_site_key`, `logo_url`, `logo_mobile_url`, `og_image_url`,
`watermark_url`, `primary_color`, `secondary_color`, `realtors_page_slug`,
`results_per_page`, `thumbnail_max_width`, `thumbnail_max_height`,
`watermark_position`, `menu_items[]` (`id`, `label`, `path`, `sort_order`,
`is_active`, ordenados por `sort_order`), `legacy_id`, `created_at`,
`updated_at`.

## POST /api/v1/portals/

Obrigatórios: `slug` (único), `name`, `domain` (único), `main_city` (UUID),
`email`, `seo_title`, `seo_description`.

Opcionais: `extra_domains` (lista), `is_active` (default `true`), `cities`
(lista de UUID — vira `PortalCity` na ordem enviada), `combined_portals`
(lista de UUID; não pode conter o próprio portal), `show_city_filter`,
`phone`, `whatsapp`, `address`, `seo_keywords`, `about_text`, `facebook_url`,
`instagram_url`, `ga4_measurement_id`, `recaptcha_site_key`, `primary_color`,
`secondary_color`, `realtors_page_slug` (default `imobiliarias`),
`results_per_page` (default 30), `thumbnail_max_width` (360),
`thumbnail_max_height` (230), `watermark_position` (9), `menu_items` (lista de
`{label, path, sort_order, is_active}`), imagens `logo`, `logo_mobile`,
`og_image`, `watermark`.

Imagens vão em `multipart/form-data`. Listas aninhadas (`menu_items`) exigem
body `application/json`; em multipart envie só campos escalares e imagens
(`cities`/`combined_portals` em multipart funcionam como chave repetida).
`null` numa imagem remove o arquivo.

`data`: todos os campos de escrita (imagens voltam só como `*_url`) +
`cities`, `combined_portals`, `menu_items`, `created_at`, `updated_at`.
Erros: `400` (validação; `error.combined_portals` se incluir o próprio
portal), `403`.

## PUT/PATCH /api/v1/portals/{id}/

Mesmos campos do POST. Enviar `cities`, `combined_portals` ou `menu_items`
substitui a lista inteira; omitir mantém. `menu_items` são recriados (os `id`
mudam). `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/portals/{id}/

Remoção física em cascata de `PortalCity`, `PortalMenuItem`, banners, ads,
dicas e posts. Falha (`PROTECT`) se houver anunciantes, leads ou contatos
vinculados.

## GET /api/v1/portals/lookup/

Sem paginação, só `is_active=true`. Aceita `search` e `main_city`.
`data[]`: `key` (id), `value` (`name`).
