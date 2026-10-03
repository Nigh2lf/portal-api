# Auth & Permissions

JWT, o eixo `is_staff` × `role`, classes prontas e como usá-las.

## Autenticação

### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/login/` | Recebe `{email, password}` → retorna `{access, refresh, name, permissions}` ([contrato](../core/modules/auth/docs/index.md)). |
| POST | `/api/v1/auth/refresh/` | Recebe `{refresh}` → novo `{access}` (rotaciona refresh). |
| POST | `/api/v1/auth/logout/` | Recebe `{refresh}` → adiciona ao blacklist. |

Tokens JWT (HS256) gerados pelo SimpleJWT. Configuração em [configuration.md](configuration.md#jwt-simplejwt).

### Uso no front

```http
GET /api/v1/users/me/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Blacklist

`rest_framework_simplejwt.token_blacklist` está em `INSTALLED_APPS`. Logout invalida o refresh; rotação invalida o anterior automaticamente.

## Os dois eixos: `is_staff` × `role`

São **independentes**. Não confunda.

| Atributo | O que controla | Onde checa |
|---|---|---|
| `User.is_staff` | Acesso ao **Django Admin** (`/admin/`) e à doc OpenAPI. | Usado pelo Django nativamente. |
| `User.role` | Papel de **negócio** na API REST. Valores: `User.Role.ADMIN`, `User.Role.USER`. | Classes em `core.classes.permission_role`. |

Ou seja:
- Um suporte interno pode ter `is_staff=True` (acessar admin) e `role=USER` (na API age como cliente).
- Um cliente premium pode ter `role=ADMIN` (poder elevado na API) sem `is_staff` (não entra em `/admin/`).

## Classes de permissão

Em [core/classes/permission_role.py](../core/classes/permission_role.py):

| Classe | Permite |
|---|---|
| `IsAdminRole` | Apenas `role=ADMIN`. |
| `IsUserRole` | Apenas `role=USER`. |
| `IsAnyRole` | Qualquer `role` válido (basicamente "autenticado com role definido"). |

Em [core/classes/permission.py](../core/classes/permission.py):

| Classe | Permite |
|---|---|
| `CustomPermissionClass` | **Padrão do projeto.** Checa `Permission` cadastrada em DB para o `Menu` correspondente ao ViewSet, via `Profile` → `ProfilePermission` → `Permission`. **Fail-closed**: se o ViewSet não declarar `view_name`, nega tudo. |
| `SafeDefaultPermission` | Rede de segurança global — se algum ViewSet **esquecer** de declarar `permission_classes`, leituras passam mas escritas (POST/PUT/PATCH/DELETE) são bloqueadas. |

## Defesa em profundidade contra ViewSet exposto

O cenário "dev cria ViewSet sem permissão e deploya por engano" é blindado em **3 camadas**:

1. **System check (boot)** — [core/checks.py](../core/checks.py) varre o `router` em `config/urls_v1.py` e **derruba o boot** (`manage.py runserver`, `test`, `check`, `migrate`) se algum ViewSet:
   - `core.E001` — não declara `permission_classes` nem `get_permissions`.
   - `core.E002` — usa `CustomPermissionClass` mas não tem `view_name`.
   - `core.W002` — herda de `BaseModelViewSet`, expõe `destroy` e usa `permission_classes` uniforme (mesmo nível para ler e deletar). Não dispara com `CustomPermissionClass`, que já separa por método HTTP.

2. **Test de auditoria** — [core/tests/test_basics.py::PermissionAuditTests](../core/tests/test_basics.py) replica o mesmo na CI.

3. **Runtime guard** — `SafeDefaultPermission` está no `DEFAULT_PERMISSION_CLASSES` global. Se alguém suprimir os checks, escritas continuam bloqueadas em runtime para qualquer ViewSet sem perms próprias.

> Resultado: declarar permissão (`view_name` + `CustomPermissionClass`) **deixa de ser opcional**.

## Checks de hardening de produção

Rodam apenas em `manage.py check --deploy` (use na CI/CD antes do deploy):

| ID | Trava |
|---|---|
| `core.E004` | `SECRET_KEY` fraca/default em prod (< 50 chars ou contém "change-me", "dev", etc.) |
| `core.E005` | `ALLOWED_HOSTS` vazio ou contendo `*` em prod |
| `core.E006` | `CORS_ALLOW_ALL_ORIGINS=True` em prod |
| `core.E008` | Migrations pendentes em prod (derruba o boot) |
| `core.W003` | `NOCLAF_API_KEY` ausente em prod (e-mails/CEP falham silenciosamente) |
| `core.W004` | `SECURE_SSL_REDIRECT=False` em prod |
| `core.W006` | `AllowAny` usado sem comentário `# allow-any: <motivo>` |
| `core.W007` | `ModelSerializer.Meta.fields = "__all__"` (proibido) |
| `core.W008` | Serializer expõe campo PII (`password`, `forgot_password_hash`, `email_verification_code`, …) sem `Meta.allow_pii = True` |

Combine com o `--deploy` nativo do Django para uma checagem completa:

```bash
DEBUG=False python manage.py check --deploy --fail-level WARNING
```

### Exemplo: ViewSet com permissões fixas

```python
from rest_framework import permissions
from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission_role import IsAdminRole

class ProductViewSet(BaseModelViewSet):
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminRole()]
```

### Padrão do projeto: `CustomPermissionClass`

```python
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass

class ProductViewSet(BaseModelViewSet):
    view_name = "product"
    permission_classes = [IsAuthenticated, CustomPermissionClass]
```

`CustomPermissionClass` casa o método HTTP com `Permission.type` e checa se o
usuário tem essa permission via algum `Profile` ativo. Cadastre os registros com
[`seedpermissions`](management-commands.md#seedpermissions).

| Método HTTP | `Permission.type` exigido |
|---|---|
| GET | `READ` (list e retrieve compartilham) |
| POST | `CREATE` |
| PUT / PATCH | `UPDATE` |
| DELETE | `DELETE` |

### Atributos da ViewSet

| Atributo | Default | O que faz |
|---|---|---|
| `view_name` | — (**obrigatório**) | Nome da permissão em snake_case, único. Casa com `Menu.view`. Sem ele, nega tudo. |
| `router_user` | `None` | Lista de `User.role` que podem acessar (ex.: `["ADMIN"]`). Papel fora da lista leva 403 antes da consulta ao DB. `None` = qualquer papel. |
| `view_read` | `False` | `True` faz **qualquer** método HTTP exigir apenas `READ`. Padrão de painel: quem enxerga a tela também opera nela. |

```python
class RelatorioViewSet(BaseViewSet):
    view_name = "relatorio_vendas"
    router_user = ["ADMIN"]      # só role ADMIN
    view_read = True             # POST/PUT/DELETE exigem só READ
    permission_classes = [IsAuthenticated, CustomPermissionClass]
```

### Actions públicas (pré-login)

Cadastro, reset de senha e afins não têm usuário para consultar. Elas saem do
padrão via `get_permissions` — sempre com o comentário `# allow-any:` exigido
pelo check `core.W006`:

```python
class ProductViewSet(BaseModelViewSet):
    view_name = "product"
    permission_classes = [IsAuthenticated, CustomPermissionClass]

    def get_permissions(self):
        # allow-any: catálogo é exibido na landing page anônima.
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return super().get_permissions()
```

## Acessar a doc OpenAPI

Mesmo com `DEBUG=True`, Swagger e Redoc exigem login admin:

```python
SPECTACULAR_SETTINGS = {
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SERVE_AUTHENTICATION": ["rest_framework.authentication.SessionAuthentication"],
}
```

Login em `/admin/` (sessão Django) dá acesso a:
- `GET /api/v1/docs/swagger/`
- `GET /api/v1/docs/redoc/`
- `GET /api/v1/schema/`

## MFA no Django Admin

O boilerplate já vem com `django-otp` instalado. Os models (TOTPDevice, StaticDevice) existem sempre, mas a exigência de código no login do `/admin/` só liga via env:

```bash
ADMIN_MFA_ENABLED=True
```

Quando ativo, `admin.site` é trocado por `OTPAdminSite` em [core/admin.py](../core/admin.py) e o middleware `django_otp.middleware.OTPMiddleware` (já registrado em qualquer modo) passa a ser usado para validar o token.

**Cadastro do dispositivo** (faça com o flag desligado para evitar travar fora):

1. `/admin/otp_totp/totpdevice/add/` → escolha o user, marque **Confirmed**, salve, escaneie o QR Code.
2. (Backup) `python manage.py addstatictoken <email>` gera um token de uso único.
3. Ligue `ADMIN_MFA_ENABLED=True` e reinicie.

> Se você ligar o flag **antes** de cadastrar um device, o login no admin trava. Volte para `False`, cadastre, religue.

## Forgot password

Fluxo:

1. `POST /api/v1/users/forgot-password/` com `{email}` → gera `forgot_password_hash`, expira em 1h, envia e-mail com link `URL_FORGOT_PASSWORD?email=...&hash=...`.
2. Front recebe o token na URL e mostra formulário de nova senha.
3. `POST /api/v1/users/change-password-forgot-password/` com `{email, hash, password}` → troca a senha.

Toda troca de senha (admin, fluxo logado, reset) dispara `User.set_password()` que **invalida** automaticamente qualquer token pendente.
