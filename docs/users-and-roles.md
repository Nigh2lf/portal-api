# Users & Roles

Tudo sobre o modelo `User`, criação, soft delete, profiles e permissions.

## Model `User`

Em [core/models.py](../core/models.py):

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK. |
| `email` | EmailField unique | Normalizado para lowercase em `save()` e em `UserManager._normalize`. |
| `name` | CharField (opcional) | |
| `password` | hash | Setado via `set_password`. |
| `profile_image` | ImageField | Privado (vai para `MediaStorage`). |
| `is_staff` | bool | Acesso ao Django Admin. |
| `is_active` | bool | Soft delete também marca `False`. |
| `role` | choice (`ADMIN`/`USER`) | Negócio. |
| `email_verified` | bool | Ver [email-verification.md](email-verification.md). |
| `email_verification_code` / `_expire` | — | Idem. |
| `forgot_password_hash` / `_expire` | — | Token de reset. |
| `created_at` / `updated_at` / `deleted_at` / `deleted_by` | timestamps + auditoria | |
| `profiles` | M2M `Profile` via `UserProfile` | |

### Helpers

| Método | O que faz |
|---|---|
| `set_password(raw)` | Hash + invalida `forgot_password_hash`. |
| `is_admin_role` (property) | `True` se `role==ADMIN`. |
| `delete(deleted_by=None)` | Soft delete (`is_active=False`, `deleted_at=now()`). |
| `generate_email_verification_code()` | Gera código de 6 dígitos. |
| `confirm_email_verification(code)` | Compara via `secrets.compare_digest`. |

## Endpoints

Sob `/api/v1/users/`:

| Método | Path | Auth | Descrição |
|---|---|---|---|
| GET | `/` | login | Lista (com `search_fields=["id","name","email"]`). |
| GET | `/{id}/` | login | Detalhe. |
| POST | `/` | público | Cadastro. Dispara welcome ou código de verificação. |
| PUT/PATCH | `/{id}/` | login | Atualiza. |
| DELETE | `/{id}/` | login | Soft delete. |
| GET | `/me/` | login | Usuário logado. |
| POST | `/forgot-password/` | público (throttled) | `{email}` → envia link. |
| POST | `/change-password-forgot-password/` | público | `{email, hash, password}`. |
| POST | `/change-password/` | login | Troca senha logado. |
| GET | `/lookup-profile/` | login | Lista de `Profile` ativos para selects. |
| POST | `/send-verification-code/` | público (throttled) | Reenvia código. |
| POST | `/verify-email/` | público | Confirma código. |

## Soft delete

`User.delete(deleted_by=request.user)` marca `is_active=False`, registra `deleted_at` e `deleted_by`. ViewSets do boilerplate filtram `deleted_at__isnull=True` no `get_queryset`.

Para hard delete (raro): manipule via `UserManager` direto.

## Profiles & Permissions

Sistema dinâmico para granular o acesso por `Menu`/`type`:

```
User ──M2M── UserProfile ──FK── Profile ──M2M── ProfilePermission ──FK── Permission ──FK── Menu
```

- `Menu` representa um recurso (ex: "users", "products").
- `Permission` é uma ação por menu (`READ`, `CREATE`, `UPDATE`, `DELETE`).
- `Profile` agrupa permissões em um perfil (ex: "Vendas", "Financeiro").
- `UserProfile` liga usuário ao perfil.

### Cadastrar permissões

- Manualmente: comando [`createpermission`](management-commands.md#createpermission).
- Automaticamente a partir dos ViewSets registrados: [`seedpermissions`](management-commands.md#seedpermissions).

### Checar nas views

Use `CustomPermissionClass`:

```python
from core.classes.permission import CustomPermissionClass

class OrderViewSet(BaseModelViewSet):
    permission_classes = [IsAuthenticated, CustomPermissionClass]
```

A classe casa `action` ↔ `Permission.type`:

| Action DRF | Permission.type |
|---|---|
| `list` / `retrieve` | `READ` |
| `create` | `CREATE` |
| `update` / `partial_update` | `UPDATE` |
| `destroy` | `DELETE` |

## Criação de usuário

| Caminho | Quando usar |
|---|---|
| `python manage.py createuser` | **Primeiro admin** ou seeders. |
| `POST /api/v1/users/` | Cadastro normal pela API. Dispara welcome (ou código de verificação se opt-in). |
| Django Admin (`/admin/`) | Manutenção. |
