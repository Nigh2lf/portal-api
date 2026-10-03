# Me (anunciante logado)

`view_name`: `advertiser_me` · papéis: `USER`, `ADMIN` (perfil `ANUNCIANTE`, `view_read`) ·
base: `/api/v1/advertiser/me/`

Toda resposta usa o envelope `{success, status, message, data, error}`. O
anunciante é sempre o do usuário da sessão (`user.advertiser_profile`); usuário
sem anunciante recebe `404` com `message` = "Usuário sem cadastro de anunciante.".

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/me/` | `READ` |
| PATCH | `/api/v1/advertiser/me/` | `READ` (`view_read`) |
| POST | `/api/v1/advertiser/me/change-password/` | `READ` (`view_read`) |
| GET | `/api/v1/advertiser/me/plan-usage/` | `READ` |

## GET /api/v1/advertiser/me/

`data`: `advertiser_id`, `user_id`, `name`, `email`, `type` (`OWNER` | `BROKER` |
`AGENCY`), `portal_slug`, `plan` (`id`, `slug`, `name`, `property_limit`,
`photo_limit`, `featured_limit`, `has_hotsite`, `has_realtor_page`,
`receives_property_requests`, `monthly_price`), `has_automatic_import`
(integração com `xml_url` preenchida), `has_hotsite`, `is_published`,
`document`, `phone`, `phone_secondary`, `whatsapp`, `contact_name`, `website`,
`address`, `creci`, `created_at`.

## PATCH /api/v1/advertiser/me/

Body (todos opcionais): `name`, `email`, `phone`, `phone_secondary`,
`whatsapp`, `contact_name`, `website`, `address`, `creci`. `name` e `email`
também atualizam o usuário de login.

`data`: mesmo payload do GET.
Erros: `400` (validação; `error.email` quando o e-mail já pertence a outro
usuário).

## POST /api/v1/advertiser/me/change-password/

Body: `{"old_password", "new_password"}` (o front envia MD5 em maiúsculas; a
API trata como senha literal).

`data`: `{"ok": true}`. Erros: `400` (`error.old_password` = "Senha atual
incorreta."). Não envia e-mail (TODO).

## GET /api/v1/advertiser/me/plan-usage/

`data`: `plan` (mesmo bloco do GET), `properties_used` (imóveis ativos e não
excluídos), `featured_used` (ativos em destaque), `photo_limit` (limite
efetivo de fotos por imóvel: override do anunciante ou o do plano).
