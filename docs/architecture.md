# Architecture

Layout de pastas, camadas e padrões usados no boilerplate.

## Estrutura

```
config/                  # settings, urls, storage S3
core/                    # único app do boilerplate
  classes/               # base classes (BaseModelViewSet, permission classes, exception handler)
  cron/                  # APScheduler (jobs.py + scheduler.py)
  management/commands/   # comandos manage.py
  migrations/
  models.py              # User, Profile, Permission, PublicAsset, etc.
  serializers/           # um arquivo por área
  services/              # integrações (e-mail, CEP)
  template_emails/       # _base.html + templates por tipo
  tests/                 # pacote de testes
  views/                 # um arquivo por viewset
docs/                    # esta documentação
manage.py
requirements.txt
requirements-dev.txt
```

## Camadas

```
HTTP request
    │
    ▼
URL router (config/urls_v1.py)
    │
    ▼
View / ViewSet (core/views/*)
    │  ── usa permissions classes (core/classes/*)
    │  ── usa serializers (core/serializers/*)
    │  ── chama services (core/services/*)
    ▼
ORM (core/models.py)
    │
    ▼
DB
```

## Envelope padrão

Todas as respostas têm o mesmo formato — sucesso ou erro:

```json
{
  "success": true,
  "status": 200,
  "message": "",
  "data": { ... },
  "error": null
}
```

Implementado em [core/classes/exception_handler.py](../core/classes/exception_handler.py):

- `envelope_success(data, http_status)` para retornos manuais.
- `envelope_exception_handler` registrado no `REST_FRAMEWORK["EXCEPTION_HANDLER"]` — converte qualquer `APIException` em envelope.

Erros não tratados (`Exception`) viram `500` com `error.detail` genérico (e log completo no servidor).

## BaseModelViewSet

`core.classes.base_viewset.BaseModelViewSet` estende `ModelViewSet` e dá:

- Envelope automático em `list/retrieve/create/update/destroy`.
- `transaction.atomic` em `create`, `update`, `destroy`.
- `destroy` chama `instance.delete(deleted_by=request.user)` (soft delete se aplicável).
- Helper `_response_format(success, status, message="", data=None, error=None)`.

### Exemplo

```python
from rest_framework import permissions
from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission_role import IsAdminRole
from core.models import Product
from core.serializers import ProductSerializer


class ProductViewSet(BaseModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    search_fields = ["name", "sku"]
    ordering_fields = ["created_at", "name"]
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminRole()]
```

Registre em [config/urls_v1.py](../config/urls_v1.py):

```python
router.register(r"products", ProductViewSet, basename="product")
```

## Models — convenções

- **PK UUID** sempre: `id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
- **Timestamps**: `AbstractModel` traz `created_at` / `updated_at` + `ordering = ("-created_at",)`.
- **Auditoria de autoria**: `AbstractModel` também traz `created_by` / `updated_by` (FK opcional para `User`, `editable=False`, `on_delete=SET_NULL`). São populados automaticamente pelo `BaseModelViewSet` em `perform_create` / `perform_update` quando o usuário está autenticado. Em fluxos sem request (shell, management commands, jobs) ficam `NULL`.
- **Soft delete opt-in**: herdar `SoftDeleteMixin` (adiciona `deleted_at`, `deleted_by`, `objects.alive()`, `delete(hard=False)`).
- **`__str__`** definido em todos os models (admin fica legível).

## Serializers

Um arquivo por domínio em `core/serializers/`. Re-exportados em `core/serializers/__init__.py`.

Padrão: `ModelSerializer` com `Meta.fields` explícito (nunca `__all__` em models com PII).

## Services

Integrações externas isoladas em `core/services/`. Regras:

- **Não levantam exceções** que cheguem na view. Retornam `bool` ou tupla `(data, error)`.
- Chamadas HTTP via `urllib.request` (zero deps extras).
- Timeout sempre via settings (`EMAIL_API_TIMEOUT`, `CEP_API_TIMEOUT`).
- Erros são logados via `logging` (logger por módulo).

## Tests

Pacote [core/tests/](../core/tests/). Estilo pytest funcional + fixtures (pytest-django + pytest-mock). Roda com:

```bash
pytest core
```

Detalhes em [testing-and-quality.md](testing-and-quality.md).

## Cron

Jobs em background via APScheduler. Liga com `RUN_CRON=true`. Detalhes em [cron.md](cron.md).
