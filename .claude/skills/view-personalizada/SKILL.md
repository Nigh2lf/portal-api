---
name: view-personalizada
description: >
  Cria uma viewset personalizada neste boilerplate (app `core`) com BaseViewSet —
  sem CRUD automático: você implementa os métodos nativos que precisar
  (list/create/update/retrieve/destroy) e/ou `@action`. Para relatórios, painéis,
  endpoints de serviço e CRUD com controle manual. Use quando o usuário pedir
  "criar view personalizada", "endpoint de relatório/painel", "view com controle
  manual do CRUD", ou quando o recurso não encaixa no CRUD automático do
  BaseModelViewSet (para CRUD padrão de model use a skill view-crud-completo).
---

# Criar view personalizada (BaseViewSet)

Cria uma viewset herdando de
[BaseViewSet](../../../core/classes/base_viewset.py) — **sem CRUD automático**
(diferente do `BaseModelViewSet`): você escreve o corpo de cada endpoint. Pode
usar os **métodos nativos** do ViewSet (`list`, `retrieve`, `create`, `update`,
`partial_update`, `destroy`) — o router os mapeia para as rotas REST padrão — e
`@action` para endpoints extras. De `BaseViewSetMixin` herda `allowed_lookups`,
`pagination_class` e os helpers de raw SQL.

As **regras transversais** (camadas view/serializer/service, comentários,
permissões, regras invioláveis do CI) estão no [CLAUDE.md](../../../CLAUDE.md) —
siga-o, não repita aqui.

- **Quando NÃO usar**: se é CRUD de model (list/retrieve/create/update/destroy
  padrão), use a skill [view-crud-completo](../view-crud-completo/SKILL.md) com
  `BaseModelViewSet` — ele já entrega envelope, transação, soft delete e
  auditoria de graça.

## 0. Antes de começar — pergunte (em português)

1. **Nome do módulo** — `snake_case` (define `core/modules/<modulo>/`).
2. **`view_name`** — `snake_case` único; casa com `Menu.view` (§5).
3. **`router_user`** — `["ADMIN"]`, `["USER"]` ou omitir. Papéis válidos: os de
   `User.Role`.
4. **`view_read`** — painel ("quem vê, opera") → `True`.
5. **Endpoints** — quais métodos nativos e/ou `@action`: verbo HTTP, `url_path`,
   entrada e saída de cada um.
6. **Fonte de dados** — ORM (com serializer) ou raw SQL? Ver §3 antes de
   prometer raw SQL.
7. **`allowed_lookups`** — hoje só existe `lookup_usuario`
   ([core/modules/lookup/view.py](../../../core/modules/lookup/view.py)); se
   pedirem outro, **alerte**, não invente.

## 1. Estrutura de pastas

```
core/modules/<modulo>/
├── __init__.py         # vazio
├── view.py             # <Nome>ViewSet (actions finas)
├── serializer.py       # só se algum endpoint serializa model
├── service/            # regra de domínio (obrigatório p/ lógica não trivial)
│   ├── __init__.py
│   └── <modulo>_service.py
└── docs/
    └── index.md        # contrato para o frontend (obrigatório, §6)
```

Estrutura **plana** — não crie níveis de "ambiente". Serializer (se houver) pela
skill [padronizar-serializer](../padronizar-serializer/SKILL.md).

## 2. `view.py`

`BaseViewSet` **não** implementa CRUD, mas o router **roteia os métodos nativos**
que você definir: `list` → `GET /base/`, `create` → `POST /base/`, `retrieve` →
`GET /base/{pk}/`, `update` → `PUT`, `partial_update` → `PATCH`, `destroy` →
`DELETE /base/{pk}/`. Defina **só os que precisar**; `@action` apenas para
endpoints **além** desses seis.

```python
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.modules.<modulo>.service import PainelService


class PainelViewSet(BaseViewSet):
    view_name = "painel"
    router_user = ["ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    allowed_lookups = ["lookup_usuario"]

    def list(self, request, *args, **kwargs):
        """GET /api/v1/painel/ — resumo do painel."""
        return envelope_success(data=PainelService().resumo(request.query_params))

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """POST /api/v1/painel/ — dispara o processamento."""
        data = PainelService(user=request.user).processar(request.data)
        return envelope_success(data=data, http_status=201)

    @action(detail=False, methods=["get"], url_path="por-usuario/(?P<user_id>[^/.]+)")
    def por_usuario(self, request, user_id=None, *args, **kwargs):
        """GET /api/v1/painel/por-usuario/{user_id}/ — consulta fora do CRUD."""
        return envelope_success(data=PainelService().por_usuario(user_id))
```

Regras (o CLAUDE.md manda — só cumpra):

- **Resposta sempre no envelope.** Como não há CRUD gerado, cada método monta a
  própria resposta com `envelope_success(data=..., http_status=...)` (ou
  `self._response_format(True, status, data=...)`). Erro levantado como exceção
  do DRF (`ValidationError`, `PermissionDenied`, `NotFound`) já sai envelopado
  pelo [exception_handler](../../../core/classes/exception_handler.py) — não
  monte resposta de erro na mão.
- **Escrita não é atômica aqui** (isso é do `BaseModelViewSet`): decore você
  mesmo com `@transaction.atomic` todo método/action que grava.
- **Método/action fino**: resolve o objeto (`get_object_or_404`), chama o
  service, devolve o envelope. Regra de domínio mora em `service/` (CLAUDE.md
  §1.3); validação de campo, no serializer.
- **Soft delete**: `destroy` aqui é seu — em model com `SoftDeleteMixin` chame
  `instance.delete(deleted_by=request.user)`, nunca delete físico.
- **`created_by`/`updated_by`** também não vêm de graça: passe no `save()`.
- **Action pública** (pré-login) → `get_permissions` com o comentário
  `# allow-any: <motivo>` (sem ele, check `core.W006`).
- **Classe não leva docstring**; docstring curta nos métodos, dizendo o que faz.
- **`*args, **kwargs`** em actions com captura no `url_path` — os grupos da regex
  chegam como kwargs.

### Paginação

`BaseViewSet` não é `GenericAPIView`: **não existe** `self.paginate_queryset`.
Pagine à mão com a `pagination_class` (default
[StandardPagination](../../../core/classes/pagination.py)):

```python
def list(self, request, *args, **kwargs):
    queryset = Model.objects.filter(is_active=True)
    paginator = self.pagination_class()
    page = paginator.paginate_queryset(queryset, request, view=self)
    serializer = ModelListSerializer(page, many=True)
    return envelope_success(data=paginator.get_paginated_response(serializer.data).data)
```

Precisa de `search`/`ordering`/`filterset_fields` prontos? Isso é
`GenericAPIView` — ou você filtra na mão pelo `request.query_params`, ou o caso
era CRUD e a skill certa é a [view-crud-completo](../view-crud-completo/SKILL.md).

## 3. Raw SQL (relatórios)

Prefira ORM. Se o relatório realmente exigir SQL, `BaseViewSetMixin` expõe
`self.execute_query(sql, params)` e `self.paginated_raw_sql(query, params,
request)` (este devolve o mesmo formato da `StandardPagination`, e a query deve
trazer `COUNT(*) OVER() AS total_registros`, sem `LIMIT`/`OFFSET` inline).

> ⚠️ Os dois dependem de `core/services/execute_sql.py`, que **não existe no
> repo** — chamá-los hoje levanta `ModuleNotFoundError`. Antes de usar raw SQL,
> avise o usuário e combine a criação desse service.

Se for em frente: SQL numa constante de módulo (`queries.py` do módulo), **todo**
valor de request via `%s` (zero f-string com dado do usuário), ordenação por
whitelist e o resultado no envelope.

## 4. Registrar

1. **[core/serializers/\_\_init\_\_.py](../../../core/serializers/__init__.py)** —
   só se criou `serializer.py`: import explícito + `__all__` (ordem alfabética).
2. **[core/views/\_\_init\_\_.py](../../../core/views/__init__.py)**:
   ```python
   from core.modules.<modulo>.view import PainelViewSet
   ```
3. **[config/urls_v1.py](../../../config/urls_v1.py)** — importe de `core.views`
   (nunca do caminho profundo). Tudo aqui é montado sob `/api/v1/`:
   ```python
   router.register(r"painel", PainelViewSet, basename="painel")
   ```
   `basename` é **obrigatório** — `BaseViewSet` não tem `queryset`.

## 5. Menu + Permission (obrigatório — sem isso a rota dá 403)

Idêntico ao CRUD: crie o `Menu` com `view` **igual** ao `view_name`, as
`Permission` dos tipos usados pelos seus endpoints (`READ` p/ GET, `CREATE` p/
POST, `UPDATE` p/ PUT/PATCH, `DELETE`) e vincule a um `Profile`. Passo a passo,
comando e snippet de menu pai na
[view-crud-completo §5](../view-crud-completo/SKILL.md). **Confirme com o usuário
antes de executar — grava no banco.**

```bash
python manage.py createpermission READ --name "Painel" --view painel
```

Com `view_read = True`, todos os métodos exigem só o `READ` — basta essa
permission. Sem ele, crie um tipo para cada verbo exposto.

## 6. Documentação (obrigatória)

`core/modules/<modulo>/docs/index.md` com o contrato de **cada endpoint**
(nativo ou action: método, URL, query params, body, resposta dentro do envelope,
erros) — sem doc a viewset **não está pronta**. Não invente endpoint/campo que
não exista no code path real.

> **Testes:** criar viewset **não** exige escrever testes. Só quando o usuário
> pedir explicitamente (regra do CLAUDE.md).

## 7. Antes de encerrar

- [ ] `view_name` `snake_case` único; `permission_classes = [IsAuthenticated, CustomPermissionClass]`.
- [ ] Toda resposta de sucesso no envelope (`envelope_success`).
- [ ] Escrita com `@transaction.atomic` explícito; soft delete manual onde couber.
- [ ] Lógica de domínio em `service/`; métodos e actions finos.
- [ ] Paginação manual via `self.pagination_class` (não existe `paginate_queryset`).
- [ ] Raw SQL (se houver): `%s` em todo valor de request, ordenação por whitelist
      — e o `execute_sql` combinado com o usuário (§3).
- [ ] Registrado em `core/views/__init__.py` (e `core/serializers/__init__.py` se
      houver serializer); rota com `basename` em `config/urls_v1.py`.
- [ ] `Menu` (com `view == view_name`) + `Permission` criados e vinculados a um `Profile`.
- [ ] `docs/index.md` cobrindo todos os endpoints.
- [ ] `python manage.py check` sem erros novos (pega `core.E001`/`core.E002`) e
      `ruff check .` + `ruff format --check .` limpos.
- [ ] Resposta ao usuário (PT): arquivos criados/modificados (com links), rotas
      expostas e pontos de atenção.

## Migrar view antiga de `core/views/` para `core/modules/`

Mova o arquivo para `core/modules/<modulo>/view.py`, tire dele o que for regra de
negócio e ponha em `service/`, e **atualize os índices** (`core/views/__init__.py`
e `core/serializers/__init__.py`) — quem importa de `core.views` continua
funcionando sem saber do caminho novo. Índice desatualizado derruba a app com
`ModuleNotFoundError`.
