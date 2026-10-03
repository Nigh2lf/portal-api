# Advertiser (anunciante)

`view_name`: `advertiser` · papéis: `ADMIN` · base: `/api/v1/advertisers/`

Toda resposta usa o envelope `{success, status, message, data, error}`.
Só anunciantes não excluídos (`deleted_at IS NULL`).

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertisers/` | `READ` |
| POST | `/api/v1/advertisers/` | `CREATE` |
| GET | `/api/v1/advertisers/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/advertisers/{id}/` | `UPDATE` |
| DELETE | `/api/v1/advertisers/{id}/` | `DELETE` |
| GET | `/api/v1/advertisers/lookup/` | `READ` |

## GET /api/v1/advertisers/

Query params: `search` (`name`, `slug`, `email`, `document`, `contact_name`),
`portal` (UUID), `plan` (UUID), `type` (`OWNER` | `BROKER` | `AGENCY`),
`is_published`, `has_hotsite`, `ordering` (`name`, `slug`, `type`, `email`,
`is_published`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `slug`, `type`, `email`, `phone`, `plan`
(UUID), `plan_name`, `portal` (UUID), `portal_name`, `is_published`, `properties_count`,
`created_at`.

## GET /api/v1/advertisers/{id}/

`data`: `id`, `user` (UUID ou `null`), `user_email`, `portal`, `portal_name`,
`plan`, `plan_name`, `type`, `name`, `slug`, `document`, `email`, `phone`,
`phone_secondary`, `whatsapp`, `website`, `address`, `logo_url`, `creci`,
`contact_name`, `responsible_broker`, `notes`, `coupon`, `is_published`,
`accepted_terms_at`, `notify_by_email`, `has_hotsite`, `has_realtor_page`,
`receives_property_requests`, `property_limit`, `photo_limit`,
`featured_limit`, `super_featured_limit` (limites nulos = usa o do plano),
`integration` (objeto ou `null`), `cities` (lista de UUID de `City`),
`properties_count` (imóveis não excluídos), `legacy_id`, `created_at`,
`updated_at`.

`integration`: `id`, `integrator` (UUID ou `null`), `integrator_name`,
`xml_url`, `xml_default_url`, `save_all_images`, `skip_thumbnails`,
`is_active`, `last_imported_at`, `has_api_token` (bool),
`has_vista_credentials` (bool). Segredos (`api_token`, `vista_*`) nunca são
devolvidos.

## POST /api/v1/advertisers/

Obrigatórios: `portal` (UUID), `plan` (UUID), `type`, `name`, `email`.

Opcionais: `user` (UUID de `User`, único por anunciante), `slug` (gerado de
`name` quando ausente; único), `document`, `phone`, `phone_secondary`,
`whatsapp`, `website`, `address`, `logo` (arquivo, multipart), `creci`,
`contact_name`, `responsible_broker`, `notes`, `coupon`, `is_published`
(`false`), `accepted_terms_at`, `notify_by_email` (`true`), `has_hotsite`,
`has_realtor_page`, `receives_property_requests`, `property_limit`,
`photo_limit`, `featured_limit`, `super_featured_limit`, `cities` (lista de
UUID de `City`), `integration` (objeto).

`integration` aceita: `integrator` (UUID), `xml_url`, `xml_default_url`,
`api_token`, `vista_portal_key`, `vista_customer_code`, `vista_customer_key`,
`vista_api_url`, `save_all_images`, `skip_thumbnails`, `is_active`.

Objetos aninhados exigem body `application/json`; `logo` exige multipart
(mande num PATCH separado se precisar dos dois).

`data`: campos de escrita (sem `logo`, com `logo_url`) + `integration` (sem
segredos) + `cities` + `created_at`, `updated_at`.
Erros: `400` (validação; `error.slug` duplicado; `error.user` já vinculado),
`403`.

## PUT/PATCH /api/v1/advertisers/{id}/

Mesmos campos. `integration` enviado faz upsert campo a campo (no PATCH só os
campos informados mudam); `integration: null` remove a integração; omitir
mantém. `cities` substitui a lista inteira. `slug` vazio é regenerado.
`id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/advertisers/{id}/

Soft delete (`deleted_at`/`deleted_by`); o registro some das listagens.
Resposta `204` com `message` = "Registro deletado com sucesso!".

## GET /api/v1/advertisers/lookup/

Sem paginação. Aceita `search`, `portal`, `plan`, `type`, `is_published`.
`data[]`: `key` (id), `value` (`name`).
