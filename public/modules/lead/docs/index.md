# Public Lead (fale conosco, encomenda de imóvel, quero anunciar)

App `public` · **sem login** (`AllowAny`, throttle `public` por IP) · base:
`/api/v1/public/portals/{portal_slug}/` (rotas em `public/urls.py`, basenames
`public-contact-message`, `public-property-request`, `public-advertiser-lead`)

Formulários do `portal-web`. Toda resposta usa o envelope
`{success, status, message, data, error}`. Só há `POST`.

| Método | URL | Grava | Descrição |
|---|---|---|---|
| POST | `.../portals/{portal_slug}/contact-messages/` | `ContactMessage` | Fale conosco |
| POST | `.../portals/{portal_slug}/property-requests/` | `PropertyRequest` | Encomende seu imóvel |
| POST | `.../portals/{portal_slug}/advertiser-leads/` | `AdvertiserLead` | Quero anunciar (lead comercial) |

## Regras comuns

- `portal_slug` inexistente ou inativo → `404`.
- Corpo inválido → `400` com `error.<campo>: [mensagens]`.
- **Antispam**: depois da validação, o `email` informado e o IP do cliente
  (`X-Forwarded-For` primeiro, senão `REMOTE_ADDR`) são conferidos em
  `BlockedSender` ativo; se algum casar → `403` `"Remetente bloqueado."` e
  nada é gravado.
- `ip_address` é gravado em `ContactMessage` e `PropertyRequest`
  (`AdvertiserLead` não tem o campo).
- `recaptcha_token` é aceito e **ignorado** por enquanto (validação server-side
  pendente).
- O envio de e-mail (Noclaf) ainda não está ligado — há `# TODO` no
  `LeadService`.
- Sucesso: `201` com `data = {id}` (UUID do registro criado).

## POST .../contact-messages/

Body: `name` (obrig., ≤100), `email` (obrig., ≤120), `phone` (≤30, opcional),
`subject` (≤100, opcional), `message` (obrig., ≤4000), `recaptcha_token`
(opcional).

## POST .../property-requests/

Body:

| Campo | Tipo | Obrig. | Observação |
|---|---|---|---|
| `name` | string ≤150 | sim | |
| `email` | e-mail ≤120 | sim | |
| `phone` | string ≤30 | não | |
| `purpose` | `SALE` \| `RENT` \| `SEASONAL` | sim | |
| `property_type` | UUID \| null | não | precisa existir e estar ativo → senão `400 error.property_type` |
| `city` | UUID \| null | não | idem → `400 error.city` |
| `neighborhood` | UUID \| null | não | idem → `400 error.neighborhood` |
| `min_price` | decimal ≥ 0 \| null | não | |
| `max_price` | decimal ≥ 0 \| null | não | deve ser ≥ `min_price` → senão `400 error.max_price` |
| `is_in_condominium` | bool \| null | não | |
| `funding` | `FINANCING` \| `CASH` \| `FGTS` \| `EXCHANGE` \| `""` | não | padrão `""` |
| `message` | string ≤4000 | não | |
| `is_partner_broadcast` | bool | não | padrão `false`; marca a encomenda para repasse aos parceiros |
| `recaptcha_token` | string | não | ignorado |

`advertiser` fica sempre `null` (encomenda ao portal, não a um anunciante).

## POST .../advertiser-leads/

Body: `name` (obrig., ≤100), `email` (obrig., ≤120), `phone` (≤30, opcional),
`company` (≤120, opcional), `message` (≤4000, opcional).
