# Property (imóveis do anunciante logado)

`view_name`: `advertiser_property` · papéis: `USER`, `ADMIN` (perfil `ANUNCIANTE`,
`view_read`) · base: `/api/v1/advertiser/properties/`

Toda resposta usa o envelope `{success, status, message, data, error}`. Só
imóveis do anunciante da sessão e não excluídos (`deleted_at IS NULL`); id de
outro anunciante responde `404`. Usuário sem anunciante: `404` "Usuário sem
cadastro de anunciante.".

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/properties/` | `READ` |
| POST | `/api/v1/advertiser/properties/` | `READ` (`view_read`) |
| GET | `/api/v1/advertiser/properties/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/advertiser/properties/{id}/` | `READ` (`view_read`) |
| DELETE | `/api/v1/advertiser/properties/{id}/` | `READ` (`view_read`) |
| POST | `/api/v1/advertiser/properties/{id}/photos/` | `READ` (`view_read`) |
| DELETE | `/api/v1/advertiser/properties/{id}/photos/` | `READ` (`view_read`) |
| DELETE | `/api/v1/advertiser/properties/{id}/photos/{photo_id}/` | `READ` (`view_read`) |
| POST | `/api/v1/advertiser/properties/{id}/photos/{photo_id}/cover/` | `READ` (`view_read`) |
| POST | `/api/v1/advertiser/properties/{id}/photos/reorder/` | `READ` (`view_read`) |

## Objeto completo (listagem, detalhe e resposta de escrita)

`id`, `reference_code`, `slug`, `title`, `status` (`DRAFT` | `PUBLISHED`),
`is_active`, `is_featured`, `property_type` (`{id, name, slug}`), `city`
(`{id, name, slug, state_code}`), `neighborhood` (`{id, name, slug}` ou
`null`), `custom_neighborhood_name` (texto livre de "outro bairro"),
`is_in_condominium`, `bedrooms`, `suites`, `bathrooms`, `parking_spaces`,
`built_area`, `total_area`, `description`, `features` (lista de UUID de
`Feature`), `feature_names` (nomes com escopo `PROPERTY`),
`condominium_feature_names` (escopo `CONDOMINIUM`), `fees[]` (`id`,
`description`, `amount`, `period` = `MONTHLY` | `YEARLY` | `ONE_TIME`, `notes`),
`sale_price`, `rent_price`, `seasonal_rent_price`, `photos[]` (`id`, `url`,
`thumbnail_url`, `sort_order`, `is_cover`, `is_hosted`; ordenadas por
`sort_order`), `cover_photo_url` (miniatura da capa ou a primeira foto; `null`
sem fotos), `views_count` (total de `PropertyView`), `created_at`, `updated_at`.

Fotos de imóveis integrados por XML têm `is_hosted = false` e `url` externa;
`thumbnail_url` devolve a miniatura ou, na falta dela, a mesma `url`.

## GET /api/v1/advertiser/properties/

Query params: `search` (`reference_code`, `title`, `description`), `purpose`
(`SALE` | `RENT` | `SEASONAL`: imóveis com o preço correspondente preenchido),
`property_type` (slug), `city` (slug), `neighborhood` (slug), `status`
(`active` = ativo e publicado; `inactive` = `is_active=false`; `draft` =
`status=DRAFT`), `ordering` (`reference_code`, `title`, `is_featured`,
`sale_price`, `rent_price`, `seasonal_rent_price`, `created_at`,
`updated_at`; default `-updated_at`), `page`, `page_size`.

`data`: `count`, `total_pages`, `page`, `page_size`, `next`, `previous`,
`results[]` (objeto completo). Número de queries constante (prefetch de fotos,
características e taxas; `views_count` por `annotate`).

## GET /api/v1/advertiser/properties/{id}/

`data`: objeto completo.

## POST /api/v1/advertiser/properties/

Obrigatórios: `reference_code` (único por anunciante), `property_type` (UUID),
`city` (UUID) e ao menos um preço.

Opcionais: `is_active` (`true`), `is_featured` (`false`), `neighborhood`
(UUID ou `null`), `custom_neighborhood_name`, `is_in_condominium`, `bedrooms`,
`suites`, `bathrooms`, `parking_spaces` (inteiros, default 0), `built_area`,
`total_area`, `sale_price`, `rent_price`, `seasonal_rent_price`, `fees`
(lista de `{description, amount, period, notes}`), `description`, `features`
(lista de UUID de `Feature` ativas).

Fixos pela sessão: `advertiser` (o da sessão) e `status = PUBLISHED`. `title` e
`slug` são gerados como no painel admin (`"<tipo> <à venda|para alugar|para
temporada> em <bairro>, <cidade> - <UF>"` e slug de `"<title> <reference_code>"`).

`data`: objeto completo (`201`).
Erros `400` por campo:
- `sale_price`: "Informe ao menos um preço: venda, locação ou temporada."
- `reference_code`: "Já existe um imóvel com este código."
- `is_active`: "Seu plano permite N imóveis ativos." (ativos já no limite
  efetivo do plano/anunciante)
- `is_featured`: "Seu plano permite N imóveis em destaque."

## PUT/PATCH /api/v1/advertiser/properties/{id}/

Mesmos campos. `features` e `fees` enviados substituem a lista inteira (taxas
são recriadas, os `id` mudam); omitir mantém. Os limites só são checados quando
o imóvel **passa** a ativo/destaque. `data`: objeto completo.

## DELETE /api/v1/advertiser/properties/{id}/

Soft delete (`deleted_at`/`deleted_by`, `is_active=false`). Resposta `204`.

## POST /api/v1/advertiser/properties/{id}/photos/

`multipart/form-data` com uma ou mais partes `images`. Entram no fim da
ordenação; se não há capa, a primeira vira capa e ganha miniatura. O total de
fotos do imóvel não pode passar do limite efetivo de fotos.

Resposta `201`, `data[]`: lista completa de fotos.
Erros: `400` (`error.images` vazio/não imagem ou "Seu plano permite N fotos
por imóvel."), `404` (imóvel).

## DELETE /api/v1/advertiser/properties/{id}/photos/

Apaga todas as fotos (registros e arquivos hospedados). `data`: `[]`.

## DELETE /api/v1/advertiser/properties/{id}/photos/{photo_id}/

Apaga a foto; se era a capa, a primeira restante assume (e ganha miniatura).
`data[]`: lista completa de fotos. Erros: `404` (foto não pertence ao imóvel).

## POST /api/v1/advertiser/properties/{id}/photos/{photo_id}/cover/

Marca a foto como capa única. Sem body. `data[]`: lista completa de fotos.
Erros: `404`.

## POST /api/v1/advertiser/properties/{id}/photos/reorder/

Body: `{"ids": ["<uuid>", ...]}` na nova ordem; fotos não listadas vão para o
fim. `data[]`: lista completa de fotos. Erros: `400` (`error.ids` com UUIDs que
não pertencem ao imóvel).
