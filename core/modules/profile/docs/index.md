# Profile

`view_name`: `profile` · papéis: qualquer autenticado com permissão do menu
`profile` (sem `router_user`) · base: `/api/v1/profiles/`

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/profiles/` | `READ` |
| POST | `/api/v1/profiles/` | `CREATE` |
| GET | `/api/v1/profiles/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/profiles/{id}/` | `UPDATE` |
| DELETE | `/api/v1/profiles/{id}/` | `DELETE` |
| GET | `/api/v1/profiles/menus-permissions/` | `READ` |

## GET /api/v1/profiles/

Query params: `search` (`id`, `name`), `ordering`, `page`, `page_size`.
Só profiles ativos (`is_active=True`).

`data.results[]`: `id`, `name`, `is_active`, `created_at`.

## GET /api/v1/profiles/{id}/

`data`: `id`, `name`, `is_active`, `permissions` (lista de UUID de `Permission`),
`created_at`, `updated_at`.

## POST /api/v1/profiles/

Body: `name` (obrigatório), `is_active` (default `true`), `permissions` (lista de
UUID de `Permission`, opcional).

`data`: `id`, `name`, `is_active`, `permissions`, `created_at`, `updated_at`.
Erros: `400` (validação), `403` (sem permissão `CREATE`).

## PUT/PATCH /api/v1/profiles/{id}/

Body: `name`, `is_active`, `permissions`.

Enviar `permissions` substitui a lista inteira de vínculos; omitir mantém os
atuais. `id`, `created_at` e `updated_at` são read-only.

Toda atualização **revoga os refresh tokens** de todos os usuários vinculados ao
profile: o `POST /api/v1/auth/refresh/` deles passa a responder `401` e o front
precisa mandar o usuário logar de novo para receber o claim `permissions`
atualizado. O access token em uso continua válido até expirar
(`JWT_ACCESS_MINUTES`, default 60) — mas as permissões já valem na hora, porque
`CustomPermissionClass` consulta o banco a cada request.

## DELETE /api/v1/profiles/{id}/

`Profile` não tem soft delete — o registro é removido do banco, junto com os
vínculos `ProfilePermission` e `UserProfile` (cascade).

Resposta: `204` com `message` = "Registro deletado com sucesso!".

## GET /api/v1/profiles/menus-permissions/

Lista todos os `Menu` com as `Permission` de cada um, para montar a tela de
edição de profile. Sem paginação.

`data[]`: `id`, `name`, `view`, `permissions[]` (`id`, `menu`, `name`, `type`).
