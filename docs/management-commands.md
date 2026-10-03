# Management Commands

Comandos `manage.py` específicos do boilerplate.

## `seed_demo`

Cria usuários mínimos para um dev novo logar e testar a API em segundos. **Idempotente** — pode rodar quantas vezes quiser.

```bash
python manage.py seed_demo          # exige DEBUG=True
python manage.py seed_demo --force  # ignora a checagem (use por sua conta e risco)
```

Usuários criados:

| E-mail | Senha (humano) | Logar onde | Role | Observação |
|---|---|---|---|---|
| `admin@admin.com` | `admin` | `/admin/` (Django) | ADMIN | Superuser, senha em texto puro. |
| `admin@<projeto>.com`¹ | `admin` | API (`/api/v1/auth/login/`) | ADMIN | Front envia **MD5↑**. |
| `a@a.com` | `a` | API (`/api/v1/auth/login/`) | USER | Front envia **MD5↑**. |

¹ `<projeto>` é o slug de `PROJECT_NAME` em lowercase.

**Convenção de senha (Noclaf).** O front envia sempre `MD5(senha_humana).hex().upper()`; o backend trata esse hash como "senha bruta" e o Django aplica PBKDF2 por cima. Exemplos:

- `MD5("admin").upper()` → `21232F297A57A5A743894A0E4A801FC3`
- `MD5("a").upper()`     → `0CC175B9C0F1B6A831C399E269772661`

O superuser do Django Admin é exceção: o `/admin/` não passa pelo front Noclaf, então a senha fica em texto puro (`admin`).

> ⚠️ Não rode em produção. O comando aborta se `DEBUG=False` (a menos que use `--force`).

## `createuser`

Cria um usuário pela linha de comando. Útil para o **primeiro admin** e para seeders.

```bash
python manage.py createuser
# interativo, pergunta email, senha, role

python manage.py createuser \
  --email admin@meuapp.com \
  --password 'MinhaSenh@123' \
  --role ADMIN \
  --no-input
```

| Flag | Default | Descrição |
|---|---|---|
| `--email` | (pergunta) | E-mail (vira lowercase). |
| `--password` | (pergunta, oculto) | Senha. Validada pelas regras de [configuration.md#senha](configuration.md#senha) — exceto se passar `--no-validate`. |
| `--role` | `ADMIN` | `ADMIN` ou `USER`. |
| `--no-input` | — | Falha se faltar dado em vez de perguntar. |
| `--no-validate` | — | Pula validação de senha (use só para seed de dev). |

Quando `role=ADMIN`, o comando também marca `is_staff=True` para já dar acesso ao Django Admin.

## `createpermission`

Cria um `Menu` e suas 4 `Permission` (READ, CREATE, UPDATE, DELETE) de uma vez.

```bash
python manage.py createpermission --menu products --label "Produtos"
```

| Flag | Descrição |
|---|---|
| `--menu` | Nome técnico (ex: `products`). Casa com a action do ViewSet. |
| `--label` | Nome amigável exibido no admin. |

Idempotente: se já existir, atualiza o label.

## `seedpermissions`

Varre o `DefaultRouter` em [config/urls_v1.py](../config/urls_v1.py) e cria automaticamente um `Menu` + 5 `Permission` para cada `basename`. Use após registrar novos ViewSets:

```bash
python manage.py seedpermissions
# cria menus para users, profile, public-asset, etc. (idempotente)
```

Depois, associe `Permission`s a `Profile`s no Django Admin.

## Comandos nativos úteis

| Comando | Quando |
|---|---|
| `migrate` | Após pull / mudança em models. |
| `makemigrations core` | Após editar `core/models.py`. |
| `runserver` | Dev local. |
| `collectstatic --noinput` | Antes de deploy. |
| `shell` | REPL com Django carregado. |
| `dbshell` | Cliente do banco. |
