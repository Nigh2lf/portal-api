# AGENTS.md — Regras para IA e devs novos

> Lido automaticamente por Claude Code, Cursor, Copilot agent, Codex e por
> qualquer dev que abra o repo. **Leia antes de escrever código.**

## 1. Antes de criar QUALQUER coisa, procure

Este projeto tem padrões fortes. Reusar > recriar. Sempre.

| Vou fazer… | Procure primeiro em… | Padrão a seguir |
|---|---|---|
| ViewSet novo | `core/views/` | Herdar de `BaseModelViewSet` (`core/classes/base_viewset.py`) |
| Permissão de ViewSet | `core/classes/permission.py` | `CustomPermissionClass` + `view_name` (não invente nova) |
| Rota só para certos papéis | `core/classes/permission.py` | `router_user = ["ADMIN"]` na ViewSet |
| Tela onde "quem vê, opera" | `core/classes/permission.py` | `view_read = True` na ViewSet |
| Serializer | `core/serializers/` | Listar `fields` explicitamente. Nada de `"__all__"` (W007) |
| Model novo | `core/models.py` | UUID PK + `AbstractModel` (base com timestamps/soft-delete) |
| Admin | `core/admin.py` | `autoregister("core")` cobre o básico. Só registre manual se precisar de algo específico |
| Comando management | `core/management/commands/` | Ver `createuser.py` como template |
| Envio de e-mail | `core/services/services_emails.py` → `send_template_email()` | Não chame SMTP nem a API do provedor direto. A classe `core/services/email` (Brevo) é o único ponto de envio |
| Consulta CEP / API externa | `core/views/cep.py` | Throttle `ScopedRateThrottle` + scope dedicado |
| Endpoint **público do site** (`AllowAny`, consumido pelo portal-web) | app `public/` ([public/README.md](public/README.md)) | `public/modules/<modulo>/`, rota em `public/urls.py`, throttle `public`; nunca em `core/modules/` |
| Resposta de API | `core/classes/base_viewset.py::_response_format` | Envelope `{success, status, message, data, error}` |
| Exception handler | `core/classes/exception_handler.py` | Já configurado. Só levantar `ValidationError`, `PermissionDenied`, etc. |
| Job em background (cron) | `core/cron/jobs.py` + `core/cron/scheduler.py` | Adicione função em `jobs.py` e registre em `scheduler.start()` com `id=` + `replace_existing=True`. Ligado por `RUN_CRON=true` |
| Teste novo | `core/tests/` | Estilo pytest funcional. Use fixtures (`client`, `user`, `admin_user`), `@pytest.mark.django_db` p/ banco, `mocker` p/ patches |

**Antes de criar qualquer arquivo novo:** rode busca textual no repo pelo conceito.
Se já existe algo parecido, **estende — não duplica**.

## 1.0. Estrutura antes de iniciar a view


Antes de iniciar a view saiba:

---

## ViewSets base ([api/classes/base_viewset.py](api/classes/base_viewset.py))

| Classe | Quando usar |
|--------|-------------|
| `BaseModelViewSet` | CRUD completo. Já aplica `@transaction.atomic` em `create`/`update`/`destroy`. |
| `BaseViewSet` | Sem CRUD automático. Relatórios, painel operacional, endpoints só com `@action`. |

Ambas herdam de `BaseViewSetMixin` (paginação `BasePagination`, `dispatch` com
tratamento de erro, `execute_query`/`paginated_raw_sql`, `allowed_lookups`) e de
`LookupViewSet` (lookups reutilizáveis; exponha via `allowed_lookups = [...]`).

---

## Permissões

- **`router_user`** — tipos que podem acessar (`["GR"]`, `["CLIENTE"]`,
  `["GR", "CLIENTE"]`). `CustomPermissionClass` retorna 403 para tipo fora da lista.
- **`view_name`** — nome da permissão (snake_case, único). Em testes precisa estar
  em `DEFAULT_VIEW_NAMES` no [conftest.py](conftest.py), senão tudo dá 403.
- **`view_read = True`** (atributo opcional da viewset, default `False`) — a view
  exige **só a permissão READ** para **qualquer** método HTTP. Quem pode visualizar
  a tela acessa também POST/PUT/PATCH/DELETE dela (padrão de painel: se vê, opera).
  Internamente o `CustomPermissionClass` força `method = 'GET'`. Sem o atributo,
  cada método exige a sua permissão (CREATE/UPDATE/DELETE).
- Relatórios em [api/apps/gr/report/](api/apps/gr/report/) derivam a permissão do
  **nome da função** da action.

--- 

## ORM + Serializer (performance) — [migrar_sql_para_serializer.md](api/docs/migrar_sql_para_serializer.md)

Princípio: **nº de queries constante**, independente do volume.
- **para-um (FK/OneToOne) → `select_related`**; **para-muitos (1:N/M2M) →
  `prefetch_related`** (com `Prefetch` p/ ordenar/filtrar); **uma coluna derivada de
  muito volume → `annotate`**; **sub-dado de item de lista → batch `IN` + `context`**.
- Carregamento mora **no queryset da view**, não no serializer.
- `SerializerMethodField` **não** pode disparar query escondida em listagem (N+1).
  Use `_id` (`obj.fk_id`) ou preload. Exceção: detalhe de 1 objeto.
- Renomear/atravessar campo → `source="a.b.c"`, não method field.
- `fields = "__all__"` é anti-otimização em payload grande (e pode vazar campos
  sensíveis, ex. `*_senha`) — prefira lista explícita.
- Prove no PR: conte queries com `CaptureQueriesContext` e fixe um limite constante.

---

## Documentação

- **Toda viewset nova** precisa de `docs/index.md` (contrato p/ frontend). Sem doc,
  **a viewset não está pronta**. Gabarito:
  [ajudante_funcionario/docs/](api/apps/shared/ajudante_funcionario/docs/).
- Não invente endpoints/campos/validações na doc — cada item tem que existir no
  code path real.

> **Não crie testes de integração ao criar uma view.** Criar viewset nova **não**
> exige mais escrever testes. Só escreva testes quando o usuário pedir explicitamente
> — aí sim pytest + pytest-django (nunca `unittest.TestCase`), seeds `cli_cd_id ≥ 900050`.

---

## Comentários

Comentário explica o **porquê**, não repete o que o código já diz. Menos é mais —
comentário óbvio é **proibido**, seja `# cria o usuário` acima de
`Usuario.objects.create(...)` ou um rótulo standalone sobre algo autoexplicativo
(ex.: `# Nome/CPF do bloco` acima de um dict já claro).

- **Comente só lógica complexa** — regras não triviais, branches com significado
  de domínio, workarounds e o "porquê" de decisões. Fora disso, não comente.
- **Classe (viewset/service/serializer) não leva docstring.** Nada de descrever a
  finalidade da tela, justificar a configuração da classe (`view_name`,
  `router_user`, permissões) nem citar o endpoint legado que ela substitui — isso
  é contexto de PR/doc, não de código. Vá direto para os atributos.
  ```python
  # ❌
  class ControleVelocidadeViewSet(BaseViewSet):
      """Associação de veículos ao controle de velocidade (tela do cliente).

      Exige o serviço contratado ``csc_nu_controle_velocidade``.
      Migra ``core.views.vehicle_customer_speed``.
      """
      router_user = ["CLIENTE"]

  # ✅
  class ControleVelocidadeViewSet(BaseViewSet):
      router_user = ["CLIENTE"]
  ```
- **Docstrings curtas.** 1-3 linhas + `Args:`/`Returns:` quando houver params.
  Nunca 3-4 parágrafos explicando o óbvio.
- **Métodos de uma classe** levam docstring no padrão:
  ```python
  def metodo(self, parametro1, parametro2):
      """
      Descrição resumida do metodo

      Args:
          parametro1: dados 1
          parametro2: dados 2

      Returns:
          {...}
      """
  ```

---

## 1.1. Estrutura de views e serializers (`core/modules/`)



Todo código novo de view/serializer mora em `core/modules/`, organizado por
**ambiente** e depois por **módulo**:

```
core/modules/
├── <nome_modulo>/          # Exemplo User

```

Dentro do ambiente, **uma pasta por módulo**, com dois arquivos de nome fixo —
`view.py` e `serializer.py` (singular, sem `s`) — mais a pasta `service/` quando
o módulo tem lógica além do CRUD puro (ver **seção 1.3**):

```
core/modules/<ambiente>/<modulo>/
├── __init__.py
├── view.py
├── serializer.py
└── service/                    # opcional
    ├── __init__.py
    └── <modulo>_service.py
```


### Índice central (obrigatório)

`core/views/__init__.py` e `core/serializers/__init__.py` são o **índice** que
re-exporta o que vive em `core/modules/`. Ao criar um módulo novo, registre nos
dois lugares — o `config/urls_v1.py` e o resto do projeto importam daí, nunca do
caminho profundo:

```python
# core/views/__init__.py
from core.modules.admin.institution.view import InstitutionViewSet
from core.modules.shared.user.view import UserViewSet

__all__ = ["InstitutionViewSet", "UserViewSet"]   # mantenha em ordem alfabética
```

```python
# core/serializers/__init__.py
from core.modules.shared.user.serializer import UserSerializer
```

Esqueceu de atualizar o índice depois de mover/renomear uma pasta? A app não
sobe (`ModuleNotFoundError`). Rode `python manage.py check` depois de mexer.

> **Não renomeie `core/modules/` para `core/apps/`.** O pacote colidiria com
> `core/apps.py` (que define `CoreConfig`): em Python o diretório vence, o
> `ready()` nunca roda e você perde — silenciosamente — os system checks de
> segurança, o cron e a auditoria de models. `manage.py check` passa limpo
> mesmo assim, então a quebra não aparece.

## 1.2. Skills operacionais — use ANTES de escrever view/serializer

As skills em [.claude/skills/](.claude/skills/) são o **passo a passo executável**
destas regras (estrutura de pastas, template, permissões, registro nos índices,
rota, menu, checklist final). Este arquivo é o índice + as regras transversais;
a skill é a porta de entrada operacional.

| Tarefa pedida pelo usuário | Skill a invocar |
|---|---|
| "criar view/CRUD/endpoint", "expor o model X", "criar a viewset de …" | [`/view-crud-completo`](.claude/skills/view-crud-completo/SKILL.md) |
| "view personalizada", "endpoint de relatório/painel", "CRUD com controle manual", raw SQL | [`/view-personalizada`](.claude/skills/view-personalizada/SKILL.md) |
| "criar/ajustar/padronizar serializer", revisar um `serializer.py` | [`/padronizar-serializer`](.claude/skills/padronizar-serializer/SKILL.md) |

**Regra:** ao receber um pedido de view nova, **invoque a skill correspondente
antes de escrever a primeira linha** — não reconstrua o passo a passo de cabeça.
Na dúvida entre as duas de view: é CRUD de model → `/view-crud-completo`; não é
(relatório, painel, endpoint de serviço, CRUD manual) → `/view-personalizada`.
Criar uma view **sempre** puxa a `/padronizar-serializer` junto para os
serializers do model.

Se o pedido não encaixar em nenhuma skill, siga as seções 1.1 e 2 diretamente.

## 1.3. Camadas: serializer, view e service

Divisão de responsabilidade obrigatória em todo módulo de `core/modules/`.
Não é preferência de estilo — código fora dela volta em review.

| Camada | Faz | **Não** faz |
|---|---|---|
| `serializer.py` | declara `fields`; validação **de campo** (`validate_<campo>`); normalização de formato | `create`/`update`; consulta ao banco; regra de negócio |
| `view.py` | `get_queryset`, `get_serializer_class`, `action_permissions`, filtros; chama o service | orquestrar escrita; regra de negócio |
| `service/` | tudo que não cabe na view: validação que toca o banco, escrita de agregado, transação, efeito colateral | — |

**Quando criar service:** o momento é quando a lógica sai da view. Se é simples,
o service é uma **função** solta. Se precisa de mais de uma função, evolui para
**classe**.

**Onde mora:** na pasta do módulo (`core/modules/<ambiente>/<modulo>/service/`),
não em `core/services/`. O `core/services/` é para o que é transversal ao projeto
(e-mail, CEP, senha inicial, raw SQL). O `__init__.py` da pasta re-exporta o que
a view importa.

Referência pronta no repo: [core/modules/shared/institution/](core/modules/shared/institution/)
— serializer só com `validate_cnpj`/`validate_cpf`/tamanho de coleção, e
`InstitutionService` com unicidade de CNPJ, sincronização das coleções aninhadas,
auditoria e provisionamento de conta.

```python
# view.py — a view só amarra
def perform_create(self, serializer):
    serializer.instance = self._service().create(serializer.validated_data)

def _service(self) -> InstitutionService:
    return InstitutionService(user=getattr(self.request, "user", None))
```

**Erro de validação levantado dentro do service** usa
`rest_framework.serializers.ValidationError` com a mensagem **em lista**:

```python
raise serializers.ValidationError({"cnpj": [_("Já existe uma instituição com este CNPJ.")]})
```

Fora do `is_valid()` o DRF não passa pelo `as_serializer_error`, que é quem
normaliza escalar em lista. Sem os colchetes o front recebe uma string nesse
campo e uma lista em todos os outros 400 da mesma rota.

### Coerência na ViewSet

Se a ViewSet declara `perform_create` / `perform_update`, declare também
`create` / `update` delegando ao `super()`. O CRUD fica visível na classe em vez
de metade explícito e metade herdado:

```python
def create(self, request, *args, **kwargs):
    """Cria a instituição com os aninhados recebidos no payload."""
    return super().create(request, *args, **kwargs)

def perform_create(self, serializer):
    serializer.instance = self._service().create(serializer.validated_data)
```

O `super()` é quem monta o envelope e abre a transação (`BaseModelViewSet`) —
não reimplemente isso. `partial_update` continua caindo no `update` com
`partial=True`, não precisa de override.

## 1.4. Comentários e docstrings

**Não escreva comentários (`#`).** Única exceção: lógica genuinamente complexa,
onde o código sozinho não conta a história.

**Docstring:** curta, dizendo **o que** a função faz. Sem seção de "por quê", sem
referência a `arquivo:linha`, sem justificativa de decisão de projeto.

```python
# ✅
def _save_theme(self, institution, theme_data):
    """Cria ou atualiza o tema e reamarra o objeto na instituição."""

# ❌
def _save_theme(self, institution, theme_data):
    """Cria ou atualiza o tema.

    Dois cuidados que um update_or_create solto não teria:
    1. created_by no ramo de criação (o Django 4.2 não distingue...)
    2. institution.theme = theme invalida o cache do select_related reverso —
       sem isso o corpo da resposta do PATCH sairia com as cores antigas.
    """
```

O porquê vai na resposta ao dev, no PR ou neste arquivo — não no código.

Ficam de fora da regra (são exigência de ferramenta, não comentário):
`# allow-any: <motivo>` (W006) e `# noqa: <código> - <motivo>`.

## 2. Regras invioláveis (o CI bloqueia)

1. **Nunca** `permission_classes = []` ou ausente em ViewSet. O padrão é
   `permission_classes = [IsAuthenticated, CustomPermissionClass]` + `view_name`.
   Actions públicas (pré-login) saem do padrão via `get_permissions`.
2. **Nunca** `permissions.AllowAny` sem comentário `# allow-any: <motivo>` (W006).
3. **Nunca** `Meta.fields = "__all__"` em `ModelSerializer` (W007). Liste os
   campos. Se for read serializer realmente público, marque
   `Meta.allow_all_fields = True` como acknowledge.
4. **Nunca** expor `password`, `forgot_password_hash`, `email_verification_code`
   em saída de API (W008). Use `write_only=True` ou remova de `fields`.
5. **Nunca** `print()` em produção. Use `logging.getLogger(__name__)`.
6. **Nunca** commit de secret. `detect-secrets` no pre-commit bloqueia.
7. **Nunca** rode `pip install <x>` sem adicionar em `requirements.txt` ou
   `requirements-dev.txt` (e sem dizer ao dev).
8. **Nunca** rode nem crie migration. `makemigrations` e `migrate` são do dev —
   mexeu em model, avise e pare por aí. E nunca edite migration já mergeada.
9. **Nunca** desligue check, pre-commit hook, ou teste sem justificar no PR.
10. **Em prod:** `DEBUG=False`, `ALLOWED_HOSTS` específico, `SECRET_KEY` forte,
    `SECURE_SSL_REDIRECT=True`, `BREVO_API_KEY` setada, migrations aplicadas
    (E004/E005/W004/W003/E008 disparam se faltar).

## 3. Antes de abrir PR, rode local

```bash
# 1. Checks de segurança (bloqueia boot se falhar)
python manage.py check
python manage.py check --deploy   # simula prod

# 2. Testes
pytest core

# 3. Lint + format (já está no pre-commit)
ruff check .
ruff format --check .
```

Se algum dos 3 falhar, **não abra PR**. Conserte primeiro.

## 4. Padrão de commit

Mensagens curtas, em português, no imperativo:
- `feat: adiciona endpoint de reset de senha`
- `fix: corrige permissão de DELETE em PublicAsset`
- `chore: atualiza ruff para 0.6.0`
- `docs: explica fluxo de verificação de e-mail`

## 5. Stack (não tente trocar)

- Django 4.2 + DRF 3.14 + SimpleJWT (rotation + blacklist) + drf-spectacular
- Python 3.10+ · MySQL prod / SQLite dev · python-dotenv
- Storage: S3 (`MediaStorage` privado, `PublicMediaStorage` público) ou filesystem
- APIs externas: **Brevo** (e-mail, `BREVO_API_KEY`) e **ViaCEP** (CEP, cache em `PostalCode`).
- UUID PK em **todos** os models.
- Soft delete é **opt-in** via `SoftDeleteMixin`.

## 6. Quando precisar de contexto profundo, leia

Só abra estes arquivos quando a tarefa exigir. Não carregue tudo de cara.

| Tema | Arquivo |
|---|---|
| Visão geral | [README.md](README.md), [docs/architecture.md](docs/architecture.md) |
| Setup local | [docs/getting-started.md](docs/getting-started.md) |
| Variáveis | [docs/configuration.md](docs/configuration.md), [.env.example](.env.example) |
| Auth + permissões + checks | [docs/auth-permissions.md](docs/auth-permissions.md) |
| Users / roles | [docs/users-and-roles.md](docs/users-and-roles.md) |
| E-mail | [docs/emails.md](docs/emails.md), [docs/email-verification.md](docs/email-verification.md) |
| CEP | [docs/cep.md](docs/cep.md) |
| Public assets / S3 | [docs/public-assets.md](docs/public-assets.md) |
| Comandos manage.py | [docs/management-commands.md](docs/management-commands.md) |
| Testes / qualidade | [docs/testing-and-quality.md](docs/testing-and-quality.md) |
| Deploy | [docs/deploy.md](docs/deploy.md) |

## 7. Se você é IA: protocolo

1. **Antes de propor um arquivo novo:** confirme que não existe algo parecido
   (busca textual + listar diretório relevante).
2. **Antes de mudar lógica de auth/permissão:** leia [docs/auth-permissions.md](docs/auth-permissions.md).
3. **Antes de adicionar dependência:** justifique no PR e atualize `requirements*.txt`.
4. **Sempre rode** `manage.py check` e `pytest core` ao final. Se quebrar,
   conserte antes de devolver pro humano.
5. **Nunca** silencie um check (`# noqa`, `--no-verify`, deletar teste) sem
   pedir confirmação humana explicita. É red flag.
6. **Nunca** invente endpoint, biblioteca, env var ou padrão que não existe
   no repo. Se faltar, pergunte.
7. **Nunca** rode `makemigrations`/`migrate` (nem via script, shell ou teste).
   Alterou model? Diga ao dev qual migration falta e deixe ele rodar.

---

**TL;DR para o agente apressado:**
> Procure no repo antes de criar. Herde `BaseModelViewSet`. Liste `fields` no
> serializer. Justifique `AllowAny`. Rode `check` e `test core` antes de
> entregar. Não silencie alerta sem perguntar.
