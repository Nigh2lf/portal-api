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

## `seed_advertiser_profile`

Cria `Menu` + 4 `Permission` (READ/CREATE/UPDATE/DELETE) para cada `view_name` do app
[advertiser](../advertiser/README.md) (`advertiser_me`, `advertiser_property`,
`advertiser_inquiry`, `advertiser_property_request`, `advertiser_stats`,
`advertiser_import`) e os vincula ao perfil `ANUNCIANTE`. Essas views têm router
próprio e não aparecem no `seedpermissions`.

```bash
python manage.py seed_advertiser_profile   # idempotente
```

## Comandos nativos úteis

| Comando | Quando |
|---|---|
| `migrate` | Após pull / mudança em models. |
| `makemigrations core` | Após editar `core/models.py`. |
| `runserver` | Dev local. |
| `collectstatic --noinput` | Antes de deploy. |
| `shell` | REPL com Django carregado. |
| `dbshell` | Cliente do banco. |

## `import_legacy` — importar do portal PHP

Importa catálogos (UF, cidades, bairros, tipos, características, planos,
integradores), os **portais** e os **imóveis de um anunciante** do banco legado
para os models novos. Conecta direto no MySQL 5.7 do legado via MySQLdb (variáveis `DB_PORTAL_ANTIGO_*`; o Django 4.2 não aceita MySQL < 8 em `DATABASES`).
Idempotente: tudo é casado por `legacy_id`; rodar de novo atualiza em vez de
duplicar.

```bash
python manage.py import_legacy --client-id 5
python manage.py import_legacy --client-id 5 --skip-photos   # sem baixar fotos
python manage.py import_legacy --client-id 5 --limit 10      # teste com 10 imóveis
python manage.py import_legacy --client-id 5 --password 'Senha@123'
python manage.py import_legacy --all --skip-properties      # todos os clientes, só o cadastro (sem imóveis)
```

O que faz para o anunciante:

- Cria o `Advertiser` (tipo, plano, contatos, CRECI, limites do plano, logo) e a
  `AdvertiserIntegration` (URL do XML, integrador).
- Cria o `User` de login com o e-mail do cliente, `role=USER`, senha informada em
  `--password` ou gerada (impressa no fim; gravada no padrão MD5-upper do front).
- Importa os imóveis com título e slug gerados, características (criando as que
  não existem no catálogo), taxas (IPTU anual, demais mensais) e fotos baixadas
  das URLs do legado, com miniatura 480x320 e capa marcada.
- Preserva `updated_at` com a data de atualização do legado.
