---
name: view-crud-completo
description: >
  Cria um CRUD RESTful completo neste boilerplate (app `core`) com
  BaseModelViewSet — módulo em `core/modules/`, viewset, serializers, registro
  nos índices (`core/views/__init__.py`, `core/serializers/__init__.py`), rota em
  `config/urls_v1.py`, `Menu` + `Permission` no banco e docs. Use quando o
  usuário pedir para "criar view/CRUD/endpoint", "expor o model X", "criar a
  viewset de ...", ou migrar uma view antiga de `core/views/` para `core/modules/`.
---

# Criar CRUD completo (BaseModelViewSet)

Cria um endpoint RESTful herdando de
[BaseModelViewSet](../../../core/classes/base_viewset.py). Esta skill é o passo a
passo operacional; as **regras transversais** (camadas view/serializer/service,
comentários, permissões, regras invioláveis do CI) estão no
[CLAUDE.md](../../../CLAUDE.md) — siga-o, não repita aqui.

- Serializers: **sempre** pela skill [padronizar-serializer](../padronizar-serializer/SKILL.md).
- Não é CRUD de model (relatório, painel, endpoint de serviço)? Use a skill
  [view-personalizada](../view-personalizada/SKILL.md) com `BaseViewSet`.

## 0. Antes de começar — pergunte (em português)

Não deduza silenciosamente. Confirme com o usuário:

1. **Model** — qual model de [core/models.py](../../../core/models.py) será exposto.
2. **Nome do módulo** — `snake_case`, singular (define `core/modules/<modulo>/`).
3. **`view_name`** — `snake_case` único; é o que casa com `Menu.view` (§5).
4. **`router_user`** — `["ADMIN"]`, `["USER"]` ou omitir (qualquer papel
   autenticado). Papéis válidos: só os de `User.Role`.
5. **`view_read`** — a tela é painel ("quem vê, opera")? Então `True`.
6. **Rota** — prefixo em kebab-case (`products`, `public-assets`).
7. **Listagem** — campos exibidos, `search_fields`, `filterset_fields`, `ordering`.
8. **Menu/permissões** — nome exibido, menu pai e quais tipos criar (§5).

## 1. Estrutura de pastas

```
core/modules/<modulo>/
├── __init__.py         # vazio
├── serializer.py       # via skill padronizar-serializer
├── view.py             # <Model>ViewSet
├── service/            # só se houver lógica além do CRUD puro (CLAUDE.md §1.3)
│   ├── __init__.py
│   └── <modulo>_service.py
└── docs/
    └── index.md        # contrato para o frontend (obrigatório, §6)
```

Referência real de módulo no repo: [core/modules/lookup/](../../../core/modules/lookup/).
Estrutura **plana** (`core/modules/<modulo>/`) — não crie níveis de "ambiente".

## 2. Serializers

Crie pela skill [padronizar-serializer](../padronizar-serializer/SKILL.md).
Regras que o CI cobra: `fields` explícito (nunca `"__all__"` — W007) e nada de
`password`/`forgot_password_hash`/`email_verification_code` na saída (W008).

## 3. `view.py`

```python
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import ModelName
from core.serializers import ModelNameSerializer


class ModelNameViewSet(BaseModelViewSet):
    view_name = "model_name"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = ModelNameSerializer
    allowed_lookups = ["lookup_usuario"]
    search_fields = ["name"]
    filterset_fields = ["is_active"]
    ordering = ("-created_at",)

    def get_queryset(self):
        return ModelName.objects.filter(is_active=True)
```

**Não reescreva o CRUD.** `BaseModelViewSet` já entrega
`list`/`retrieve`/`create`/`update`/`destroy` com envelope
`{success, status, message, data, error}`, `@transaction.atomic` na escrita,
`created_by`/`updated_by` automáticos e `perform_destroy` que chama
`instance.delete(deleted_by=user)` em model com `SoftDeleteMixin`. Sobrescrever
só com motivo — e aí vale a regra de coerência do
[CLAUDE.md](../../../CLAUDE.md) ("Coerência na ViewSet"): declarou
`perform_create`, declare `create` delegando ao `super()`.

Pontos de atenção:

- **`get_queryset`** filtra o que está fora do ar: `deleted_at__isnull=True`
  (models com `SoftDeleteMixin`) ou `is_active=True`. Preload (`select_related`/
  `prefetch_related`) mora aqui, não no serializer.
- **Mais de um serializer** → `get_serializer_class` por `self.action`.
- **`allowed_lookups`** — hoje o único lookup existente é `lookup_usuario`
  ([core/modules/lookup/view.py](../../../core/modules/lookup/view.py)). Se o
  usuário pedir outro, **alerte**, não invente. Default `[]` esconde todos.
- **`authentication_classes`** é dispensável: `JWTAuthentication` já é o default
  do DRF em [config/settings.py](../../../config/settings.py).
- **Action pública** (pré-login) sai do padrão via `get_permissions` com o
  comentário `# allow-any: <motivo>` — sem ele o check `core.W006` acusa.
- **Regra de negócio** vai para `service/`; validação de campo, para o
  serializer. A viewset só amarra (CLAUDE.md §1.3).
- **Classe não leva docstring**; comentário só para lógica não óbvia.

## 4. Registrar (a ordem importa: serializer → view → rota)

1. **[core/serializers/\_\_init\_\_.py](../../../core/serializers/__init__.py)** —
   import explícito + entrada no `__all__` (ordem alfabética; **não** é wildcard):
   ```python
   from core.modules.<modulo>.serializer import ModelNameSerializer
   ```
2. **[core/views/\_\_init\_\_.py](../../../core/views/__init__.py)** — idem:
   ```python
   from core.modules.<modulo>.view import ModelNameViewSet
   ```
3. **[config/urls_v1.py](../../../config/urls_v1.py)** — importe de `core.views`
   (nunca do caminho profundo) e registre. Tudo aqui já é montado sob `/api/v1/`:
   ```python
   router.register(r"products", ModelNameViewSet, basename="product")
   ```
   `basename` é **obrigatório** quando a viewset não declara `queryset`.

## 5. Menu + Permission (obrigatório — sem isso a rota dá 403)

`CustomPermissionClass` resolve a permissão assim:

```
User → UserProfile → Profile → ProfilePermission → Permission → Menu.view == view_name
```

| Campo | Valor |
|---|---|
| `Menu.name` | nome exibido; **único** na tabela |
| `Menu.view` | **exatamente** o `view_name` da viewset — é a chave do casamento |
| `Menu.parent` | menu pai (hierarquia); `None` para menu raiz |
| `Permission.type` | `READ` (GET), `CREATE` (POST), `UPDATE` (PUT/PATCH), `DELETE` |
| `Permission.name` | rótulo livre (ex.: `"Leitura de Produtos"`) |

`unique_together = (menu, type)` — um `Permission` por tipo em cada menu. Com
`view_read = True` na viewset, todo método HTTP exige só o `READ`.

**Confirme com o usuário antes de executar — grava no banco.**

Menu raiz, via management command
([createpermission](../../../core/management/commands/createpermission.py)):

```bash
python manage.py createpermission READ CREATE UPDATE DELETE \
  --name "Produtos" --view product
```

Sem listar os tipos, cria os 4. Falha (`CommandError`) se já existir `Menu` com o
mesmo `name` — não duplica.

Com **menu pai** (o command não expõe `parent`) ou para reexecutar sem erro:

```bash
python manage.py shell -c "
from core.models import Menu, Permission
parent = Menu.objects.get(name='Cadastros')
menu, _ = Menu.objects.get_or_create(
    name='Produtos', defaults={'view': 'product', 'parent': parent}
)
for t in ['READ', 'CREATE', 'UPDATE', 'DELETE']:
    Permission.objects.get_or_create(menu=menu, type=t, defaults={'name': f'{t} de Produtos'})
print(menu.id, menu.permissions_set.count())
"
```

Por fim, **vincule as permissions a um `Profile`** — sem isso ninguém acessa:
Django Admin, ou `PATCH /api/v1/profiles/{id}/` com
`{"permissions": ["<uuid>", ...]}`. Os menus e permissions existentes saem em
`GET /api/v1/profiles/menus-permissions/`.

> ⚠️ **Não use `seedpermissions` para isto.** Ele grava `Menu.view = "/<rota>/"`
> (caminho da URL), que não casa com `view_name` — o menu criado nunca libera a
> viewset.

## 6. Documentação (obrigatória)

`core/modules/<modulo>/docs/index.md` — sem ele a viewset **não está pronta**.
Cada endpoint: método, URL, query params, body, resposta (dentro do envelope) e
erros. Não invente campo/validação que não exista no code path real.

```markdown
# <Módulo>

`view_name`: `product` · papéis: `ADMIN` · base: `/api/v1/products/`

## GET /api/v1/products/
Query params: `search`, `ordering`, `page`, `page_size`, `is_active`.
Resposta: envelope com `data.results[]` (campos …).

## POST /api/v1/products/
Body: … · Erros: `400` (validação), `403` (sem permissão CREATE).
```

> **Testes:** criar viewset **não** exige escrever testes. Só escreva quando o
> usuário pedir explicitamente (regra do CLAUDE.md).

## 7. Antes de encerrar

- [ ] `view_name` `snake_case` único; `permission_classes = [IsAuthenticated, CustomPermissionClass]`.
- [ ] `get_queryset` filtrando soft delete / `is_active`.
- [ ] CRUD herdado do `BaseModelViewSet` (não reimplementado sem motivo).
- [ ] Serializers pela skill padronizar-serializer, `fields` explícito.
- [ ] Registrado em `core/serializers/__init__.py` (antes) e `core/views/__init__.py`; rota em `config/urls_v1.py`.
- [ ] `Menu` (com `view == view_name`) + `Permission` criados e vinculados a um `Profile`.
- [ ] `docs/index.md` criado.
- [ ] `python manage.py check` sem erros novos (pega `core.E001`/`core.E002`) e
      `ruff check .` + `ruff format --check .` limpos.
- [ ] Resposta ao usuário (PT): arquivos criados/modificados (com links), rotas
      expostas e pontos de atenção.

## Migrar view antiga de `core/views/` para `core/modules/`

Mova o arquivo para `core/modules/<modulo>/view.py` (serializer de
`core/serializers/` para `serializer.py` do módulo), tire do arquivo o que for
regra de negócio e ponha em `service/`, e **atualize os dois índices** — quem
importa de `core.views` / `core.serializers` continua funcionando sem saber do
caminho novo. Índice desatualizado derruba a app com `ModuleNotFoundError`.
