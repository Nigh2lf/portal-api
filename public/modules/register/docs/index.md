# Public Register (cadastro de anunciante)

App `public` · **sem login** (`AllowAny`, throttle `public` por IP) · rota em
`public/urls.py`, basename `public-register`.

| Método | URL | Descrição |
|---|---|---|
| POST | `/api/v1/public/portals/{portal_slug}/register/` | Cria `User` + `Advertiser` e devolve os tokens JWT |

Toda resposta usa o envelope `{success, status, message, data, error}`.
`portal_slug` inexistente ou inativo → `404`.

## Body

| Campo | Tipo | Obrig. | Observação |
|---|---|---|---|
| `type` | `OWNER` \| `BROKER` \| `AGENCY` | sim | |
| `plan` | UUID | sim | plano ativo |
| `name` | string ≤120 | sim | nome do anunciante e do usuário |
| `document` | string | sim | CPF ou CNPJ; máscara é removida e devem sobrar 11 ou 14 dígitos |
| `email` | e-mail ≤120 | sim | normalizado para minúsculas; vira o login |
| `password` | string ≤128 | sim | o front envia MD5 em maiúsculas; é tratado como a senha em si (igual ao login) |
| `phone` | string ≤30 | sim | |
| `phone_secondary` | string ≤30 | não | |
| `contact_name` | string ≤80 | não | |
| `website` | URL ≤200 | não | |
| `address` | string ≤300 | não | |
| `creci` | string ≤20 | não | |
| `coupon` | string ≤45 | não | |
| `accepted_terms` | bool | sim | precisa ser `true` |

## Regras

Tudo roda em uma transação (`transaction.atomic`): qualquer erro desfaz o
cadastro inteiro.

1. `email` já existe em `User` → `400 error.email`.
2. Plano inexistente/inativo → `400 error.plan`. `OWNER` precisa usar um plano
   com `is_owner_only = true`; `BROKER`/`AGENCY` não podem usar plano
   `is_owner_only` → `400 error.plan`.
3. Cria `User` (`role = USER`, `is_active = true`, `is_staff = false`, `name`)
   com `set_password(password)` e vincula ao perfil `ANUNCIANTE`
   (`core.services.advertiser_access.grant_advertiser_access`).
4. Cria `Advertiser` no portal da URL: `slug` único a partir do nome
   (`unique_slug`), `document` só dígitos, `whatsapp` = dígitos de
   `phone_secondary` (ou de `phone`), `accepted_terms_at = agora`,
   `has_hotsite` / `receives_property_requests` copiados do plano,
   `has_realtor_page` copiado do plano **exceto** para `OWNER` (sempre `false`),
   `created_by` = o próprio usuário.
5. `is_published`: `true` quando `plan.monthly_price` é `null` ou `0`
   (grátis / sob consulta); planos pagos ficam **despublicados** até ativação
   manual pelo painel.
6. E-mails de boas-vindas/aviso ao portal ainda não são enviados (`# TODO` no
   `RegisterService`).

## Resposta `201`

`data`: `advertiser_id` (UUID), `user_id` (UUID), `is_published` (bool),
`access`, `refresh` (JWT gerados por `LoginSerializer.get_token`, com as
mesmas claims do login: `name` e `permissions`).

## Erros

| Status | Quando |
|---|---|
| `400` | campo inválido (`error.<campo>`), `document` fora de 11/14 dígitos, `accepted_terms` falso, `email` já cadastrado, `plan` incompatível/inexistente |
| `404` | portal não encontrado |
| `429` | throttle `public` |
