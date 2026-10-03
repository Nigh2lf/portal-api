# User

`view_name`: `user` · papéis: qualquer autenticado com permissão do menu `user`
(sem `router_user`) · base: `/api/v1/users/`

Toda resposta usa o envelope `{success, status, message, data, error}`.
As actions marcadas **pública** dispensam token.

| Método | URL | Acesso | Permissão |
|---|---|---|---|
| GET | `/api/v1/users/` | login | `READ` |
| POST | `/api/v1/users/` | login | `CREATE` |
| GET | `/api/v1/users/{id}/` | login | `READ` |
| PUT/PATCH | `/api/v1/users/{id}/` | login | `UPDATE` |
| DELETE | `/api/v1/users/{id}/` | login | `DELETE` |
| GET | `/api/v1/users/profile/` | login | — |
| GET | `/api/v1/users/lookup-profile/` | login | `READ` |
| POST | `/api/v1/users/forgot-password/` | **pública** (throttle `5/hour`) | — |
| POST | `/api/v1/users/change-password-forgot-password/` | **pública** (throttle `5/hour`) | — |
| POST | `/api/v1/users/send-verification-code/` | **pública** | — |
| POST | `/api/v1/users/verify-email/` | **pública** | — |

## GET /api/v1/users/

Query params: `search` (`id`, `email`, `name`), `ordering`, `page`, `page_size`.
Só usuários não deletados (`deleted_at IS NULL`).

`data.results[]`: `id`, `email`, `name`, `profile_image`, `is_active`, `role`,
`created_at`.

## GET /api/v1/users/{id}/

`data`: campos da listagem + `email_verified`, `profiles` (lista de UUID),
`updated_at`.

## POST /api/v1/users/

Body: `email` (obrigatório, único), `password` (obrigatório, passa pelos
validadores do Django), `name`, `profile_image`, `profiles` (lista de UUID de
`Profile`).

`role` (`ADMIN`/`USER`) e `is_active` são aceitos **apenas quando o solicitante
tem `role=ADMIN`**; para os demais o usuário nasce `role=USER`, `is_active=True`.
`is_staff` é sempre `False`.

Com `EMAIL_VERIFICATION_REQUIRED=True` o cadastro gera o código e envia o e-mail
de verificação; caso contrário envia o welcome. Falha no envio não derruba o
cadastro.

`data`: campos do serializer de escrita (sem `password`).
Erros: `400` (e-mail duplicado, senha ausente/fraca).

## PUT/PATCH /api/v1/users/{id}/

Body: `email`, `name`, `profile_image`, `profiles`, `password` + `old_password`.

`password` só é aceito junto com `old_password` correto — senão `400` em
`error.old_password`. Exceção: um solicitante `ADMIN` alterando **outro**
usuário pode enviar `password` sem `old_password`. `role` e `is_active` só são
gravados por solicitante `ADMIN`. Enviar `profiles` substitui a lista inteira de
vínculos. `id`, `created_at` e `updated_at` são read-only.

## DELETE /api/v1/users/{id}/

Soft delete: `is_active=False`, `deleted_at` e `deleted_by` preenchidos.
`data` vem `null`, com `message` de sucesso.

## GET /api/v1/users/profile/

Devolve o usuário do token (mesmos campos do detalhe). Só exige login — não
passa pela permissão de menu.

## GET /api/v1/users/lookup-profile/

`data`: `[{"key": <uuid do Profile>, "value": <nome>}]`, só profiles ativos.

## POST /api/v1/users/forgot-password/

Body: `email`. Gera token (`secrets.token_urlsafe`, validade 1h) e envia o
e-mail. Responde sempre `200` com `data: {"worked": true}`, mesmo para e-mail
inexistente (anti-enumeração).

## POST /api/v1/users/change-password-forgot-password/

Body: `email`, `forgot_password_hash`, `new_password`.
`200` com `data: {"worked": true}`.
Erros: `400` em `error.detail` (token inválido/expirado) ou nos validadores de
senha do Django.

## POST /api/v1/users/send-verification-code/

Body: `email`. `404` sem corpo quando `EMAIL_VERIFICATION_REQUIRED=False`.
Com a flag ligada responde `200` / `data: {"worked": true}` mesmo para e-mail
inexistente ou já verificado.

## POST /api/v1/users/verify-email/

Body: `email`, `code`. `404` sem corpo quando `EMAIL_VERIFICATION_REQUIRED=False`.
Sucesso: `200` com `data: {"worked": true, "already_verified": false}` (e-mail de
boas-vindas disparado). E-mail já verificado devolve `already_verified: true`.
Erros: `400` em `error.code` (código errado ou expirado, e-mail inexistente).
