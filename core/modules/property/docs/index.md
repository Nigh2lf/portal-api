# Property (imóvel)

`view_name`: `property` · papéis: `ADMIN` · base: `/api/v1/properties/`

Toda resposta usa o envelope `{success, status, message, data, error}`.
Só imóveis não excluídos (`deleted_at IS NULL`).

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/properties/` | `READ` |
| POST | `/api/v1/properties/` | `CREATE` |
| GET | `/api/v1/properties/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/properties/{id}/` | `UPDATE` |
| DELETE | `/api/v1/properties/{id}/` | `DELETE` |
| POST | `/api/v1/properties/{id}/photos/` | `CREATE` |
| DELETE | `/api/v1/properties/{id}/photos/{photo_id}/` | `DELETE` |
| POST | `/api/v1/properties/{id}/photos/{photo_id}/cover/` | `CREATE` |
| POST | `/api/v1/properties/{id}/photos/reorder/` | `CREATE` |

## GET /api/v1/properties/

Query params: `search` (`reference_code`, `title`, `description`),
`advertiser` (UUID), `advertiser__portal` (UUID), `property_type` (UUID),
`city` (UUID), `neighborhood` (UUID), `status` (`DRAFT` | `PUBLISHED`),
`is_active`, `is_featured`, `ordering` (`reference_code`, `title`, `status`,
`is_featured`, `sale_price`, `rent_price`, `seasonal_rent_price`,
`created_at`, `updated_at`; default `-is_featured,-updated_at`), `page`,
`page_size`.

`data.results[]`: `id`, `reference_code`, `title`, `slug`, `status`,
`is_active`, `is_featured`, `advertiser` (UUID), `advertiser_name`,
`property_type` (UUID), `property_type_name`, `city` (UUID), `city_name`,
`neighborhood` (UUID ou `null`), `neighborhood_name` (nome do bairro
vinculado ou o texto livre de "outro bairro"; `null` se nenhum), `sale_price`,
`rent_price`, `seasonal_rent_price` (decimais ou `null`), `bedrooms`,
`parking_spaces`, `cover_photo_url` (foto de capa ou a primeira; `null` sem
fotos), `updated_at`.

## GET /api/v1/properties/{id}/

`data`: `id`, `advertiser`, `advertiser_name`, `advertiser_portal` (UUID do
portal do anunciante), `reference_code`, `slug`, `title`, `status`,
`is_active`, `is_featured`, `property_type`, `property_type_name`, `city`,
`city_name`, `state_code`, `neighborhood`, `neighborhood_name` (exibição, com
fallback), `custom_neighborhood_name` (texto livre "outro bairro"),
`is_in_condominium`, `bedrooms`, `suites`, `bathrooms`, `parking_spaces`,
`built_area`, `total_area`, `description`, `sale_price`, `rent_price`,
`seasonal_rent_price`, `published_at`, `features` (lista de UUID de
`Feature`), `photos[]` (`id`, `image_url`, `thumbnail_url`, `sort_order`,
`is_cover`; ordenadas por `sort_order`), `fees[]` (`id`, `description`,
`amount`, `period` = `MONTHLY` | `YEARLY` | `ONE_TIME`, `notes`),
`cover_photo_url`, `imported_at`, `legacy_id`, `created_at`, `updated_at`.

## POST /api/v1/properties/

Obrigatórios: `advertiser` (UUID), `reference_code` (único por anunciante),
`property_type` (UUID), `city` (UUID).

Opcionais: `title` (gerado quando ausente), `slug` (gerado quando ausente;
único), `status` (`PUBLISHED`), `is_active` (`true`), `is_featured`
(`false`), `neighborhood` (UUID), `custom_neighborhood_name` (texto livre
quando o bairro não existe no cadastro), `is_in_condominium`, `bedrooms`,
`suites`, `bathrooms`, `parking_spaces` (inteiros, default 0), `built_area`,
`total_area`, `description`, `sale_price`, `rent_price`,
`seasonal_rent_price`, `published_at`, `features` (lista de UUID de `Feature`
ativas), `fees` (lista de `{description, amount, period, notes}`).

Geração automática: `title` =
`"<tipo> <à venda|para alugar|para temporada> em <bairro>, <cidade> - <UF>"`
(objetivo pelo primeiro preço preenchido, nessa ordem; sem bairro omite a
parte "<bairro>, "); `slug` = slug de `"<title> <reference_code>"`, com sufixo
numérico se já existir.

`data`: `id`, campos de escrita, `features`, `fees`, `imported_at`,
`created_at`, `updated_at`.
Erros: `400` (validação; `reference_code` duplicado no anunciante;
`error.slug` duplicado), `403`.

## PUT/PATCH /api/v1/properties/{id}/

Mesmos campos. `features` e `fees` enviados substituem a lista inteira (as
taxas são recriadas, os `id` mudam); omitir mantém. `title`/`slug` vazios são
regenerados. `id`, `imported_at`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/properties/{id}/

Soft delete (`deleted_at`/`deleted_by`, `is_active=false`). Resposta `204`.

## POST /api/v1/properties/{id}/photos/

`multipart/form-data` com uma ou mais partes `images`. As fotos entram no fim
da ordenação; se o imóvel ainda não tem capa, a primeira enviada vira capa.
`thumbnail_url` não é gerado neste endpoint (fica `null` até existir
processamento de miniaturas).

Resposta `201`, `data[]`: lista completa de fotos (`id`, `image_url`,
`thumbnail_url`, `sort_order`, `is_cover`).
Erros: `400` (`error.images` vazio/não imagem), `404` (imóvel).

## DELETE /api/v1/properties/{id}/photos/{photo_id}/

Apaga registro e arquivos. Se era a capa, a primeira foto restante assume.
Resposta `200`, `data[]`: lista completa de fotos. Erros: `404` (foto não
pertence ao imóvel).

## POST /api/v1/properties/{id}/photos/{photo_id}/cover/

Marca a foto como capa única. Sem body. Resposta `200`, `data[]`: lista
completa de fotos. Erros: `404`.

## POST /api/v1/properties/{id}/photos/reorder/

Body: `{"ids": ["<uuid>", ...]}` na nova ordem. Fotos não listadas vão para o
fim, mantendo a ordem relativa. Resposta `200`, `data[]`: lista completa de
fotos. Erros: `400` (`error.ids` com UUIDs que não pertencem ao imóvel).

## Fotos: hospedadas × externas

- Imóveis integrados por XML **não têm as fotos hospedadas**: cada `PropertyPhoto`
  guarda só `source_url` (URL no servidor do anunciante) e `is_hosted = false`.
  Somente a **capa** recebe `thumbnail` (480x320, gravada no S3 como
  `properties/thumbs/<slug-do-imovel>-<uid>.jpg`).
- Fotos enviadas pelo painel (`POST /properties/{id}/photos/`) são hospedadas
  (`image`, `is_hosted = true`, nome `properties/<slug-do-imovel>-<uid>.<ext>`);
  a capa também ganha `thumbnail`.
- `image_url` devolve a URL hospedada ou a externa; `thumbnail_url` devolve a
  miniatura ou, na falta dela, a mesma URL de `image_url`. `cover_photo_url`
  da listagem segue a mesma regra.
