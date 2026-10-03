# Auth

Login JWT · base: `/api/v1/auth/` · sem `view_name` (rota pública, pré-login).

| Método | URL | Acesso |
|---|---|---|
| POST | `/api/v1/auth/login/` | **pública** (throttle scope `login`) |
| POST | `/api/v1/auth/refresh/` | **pública** (SimpleJWT nativo) |
| POST | `/api/v1/auth/logout/` | **pública** (SimpleJWT nativo, blacklist) |

## POST /api/v1/auth/login/

Body: `email`, `password`.

Resposta **sem envelope** (view do SimpleJWT); erros passam pelo envelope padrão
(`401` credenciais inválidas, `429` throttle).

```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

`name` e `permissions` vão **dentro** dos dois tokens, como claims — o front
decodifica o `access`. Payload do access:

```json
{
  "token_type": "access", "exp": 1787064007, "iat": 1787056807,
  "jti": "...", "user_id": "98c88027-...",
  "name": "Fulano de Tal",
  "permissions": {
    "user": {"create": true, "read": true, "update": false, "delete": false}
  }
}
```

`name`: `User.name`, caindo para o e-mail quando vazio.

`permissions`: mapa `view_name` → flags CRUD. A chave é o `Menu.view`, que é o
mesmo `view_name` declarado na ViewSet e conferido pelo `CustomPermissionClass`.
Inclui os menus sem nenhuma permissão concedida (todos os flags `false`), para o
front montar a navegação com itens desabilitados. Os flags vêm dos `Profile`
**ativos** do usuário (`Profile` → `ProfilePermission` → `Permission`).
`Permission.type` `OPTIONS` não entra no mapa.

Como o mapa é assinado junto com o token, ele viaja em toda request
(~80 bytes por menu) e só reflete mudança de permissão no próximo login — o
`/refresh/` copia as claims do refresh, não reconsulta o banco.
