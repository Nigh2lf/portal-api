---
name: padronizar-serializer
description: >
  Padroniza serializers DRF da API V3 (golden-service-nova-api) no formato de 3
  serializers por model — escrita, listagem e leitura (Detail). Aplica as regras
  de performance e segurança do projeto (lista explícita de fields, sensíveis em
  write_only, sem N+1 em listagem). Use quando o usuário pedir para "padronizar
  serializer", "criar/ajustar os serializers do model X", "revisar serializer",
  ou ao criar/editar um arquivo serializer.py da V3.
---

# Padronizar Serializer (API V3)

Todo model exposto por uma viewset tem **3 serializers**, escolhidos por ação via
`get_serializer_class`. O objetivo é separar escrita, listagem e leitura, mantendo
o payload de lista enxuto e sem query escondida.

> Regras transversais valem sempre: ver [CLAUDE.md](../../../CLAUDE.md) e os guias

## Os 3 serializers

| Papel | Nome | Ações | Regra-chave |
|-------|------|-------|-------------|
| **Escrita** | `<Model>Serializer` | `create`, `update` | Todas as validações em `validate()`/`validate_<campo>()`. Sensíveis em `write_only`. |
| **Listagem** | `<Model>ListSerializer` | `list` | `fields` explícito e enxuto. **Zero query** por linha (sem `SerializerMethodField` que toca o banco). |
| **Leitura** | `<Model>DetailSerializer` | `retrieve` | `fields` explícito. `SerializerMethodField` **permitido** (é 1 objeto). Sensíveis omitidos ou `write_only`. |

Convenção de nomes deduzida do prefixo de 3 letras do model (`cli_`, `usu_`…):
id `<pfx>_cd_id`, ativo `<pfx>_bl_ativo`, sensíveis geralmente `*_senha*`, `*_token`,
`*_integracao`, `*_ws_*`.

## Templates

### Escrita — `<Model>Serializer`

```python
from rest_framework import serializers
from api.apps.<app>.models import ModelName


class ModelNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelName
        fields = [
            "mdl_cd_id",
            "mdl_tx_nome",
            # ... campos graváveis, explícitos
        ]
        # write_only para todo campo sensível que entra mas não deve voltar
        extra_kwargs = {
            "mdl_tx_senha_integracao": {"write_only": True},
        }
        # some SÓ ao substituir o UniqueTogetherValidator por validate() customizado
        # validators = []

    def validate(self, attrs):
        """
        Valida regras de domínio antes de salvar (unicidade, "já existe ativo",
        coerência entre campos). Levante serializers.ValidationError.
        """
        return attrs
```

- `fields = "__all__"` é **tolerado apenas neste serializer** (1 objeto, escrita) e
  **só** se todo campo sensível estiver em `write_only`. Na dúvida, use lista explícita.
- Regra de **negócio** (e-mail, cálculo, efeitos colaterais) **não** mora aqui — vai
  para um serviço (ver [CLAUDE.md — Onde mora a lógica](../../../CLAUDE.md)). O
  serializer só valida e mapeia.

### Listagem — `<Model>ListSerializer`

```python
class ModelNameListSerializer(serializers.ModelSerializer):
    # dado de FK na lista: use source (com select_related no queryset da view),
    # NUNCA SerializerMethodField que acessa a relação (N+1 silencioso).
    cliente_nome = serializers.CharField(source="mdl_cd_cliente.cli_tx_nome", read_only=True)

    class Meta:
        model = ModelName
        fields = [
            "mdl_cd_id",
            "mdl_tx_nome",
            "cliente_nome",
        ]
```

- Nada de `SerializerMethodField` que dispara query — é **proibido** em listagem.
- Colunas de FK via `source="fk.campo"`; o preload (`select_related`/`prefetch_related`)
  mora no `get_queryset`/`list` da view, não no serializer.

### Leitura — `<Model>DetailSerializer`

```python
class ModelNameDetailSerializer(serializers.ModelSerializer):
    # SerializerMethodField é aceitável aqui: é 1 objeto no retrieve.
    situacao = serializers.SerializerMethodField()

    class Meta:
        model = ModelName
        fields = [
            "mdl_cd_id",
            "mdl_tx_nome",
            "situacao",
        ]

    def get_situacao(self, obj):
        return "ativo" if obj.mdl_bl_ativo else "inativo"
```

## Ligar no viewset

```python
def get_serializer_class(self):
    if self.action == "list":
        return ModelNameListSerializer
    if self.action == "retrieve":
        return ModelNameDetailSerializer
    return ModelNameSerializer
```

## Registrar em `api/serializers/__init__.py`

Serializers ficam em `api/apps/<app>/serializer.py`. O
[api/serializers/__init__.py](../../../api/serializers/__init__.py) importa **um
`from api.apps.<app>.serializer import *` por app**. Verifique sempre:

- **App já registrado** (a linha do app já existe): serializer novo no mesmo
  `serializer.py` é recolhido pelo wildcard — nada a fazer no `__init__.py`.
- **App/módulo novo** (não há linha do app): **adicione**
  `from api.apps.<app>.serializer import *` ao `__init__.py`. Sem essa linha o
  serializer **não é carregado**.
- Ordem importa: serializer registrado **antes** da view (ver
  [CLAUDE.md](../../../CLAUDE.md)).

## Passo a passo (execução)

1. Identificar o model e seu arquivo `api/apps/<app>/serializer.py`.
2. Deduzir prefixo, id, `_bl_ativo` e campos sensíveis (`*_senha*`, tokens, `*_integracao`).
3. Criar/ajustar os 3 serializers pelos templates acima.
4. Definir `fields` explícito em cada um; **List** enxuta; sensíveis em `write_only`.
5. Mover validações de domínio para `validate()`/`validate_<campo>()` (com
   `Meta.validators = []` se substituir o `UniqueTogetherValidator`).
6. Remover qualquer `SerializerMethodField` de listagem que toque o banco → `source`.
7. Ligar o `get_serializer_class` na viewset.
8. Registrar em `api/serializers/__init__.py`: confirmar que o app tem a linha
   `from api.apps.<app>.serializer import *` — adicionar se for app novo.
9. Rodar `python manage.py check` — sem erros novos.

## Checklist

- [ ] 3 serializers: `<Model>Serializer`, `<Model>ListSerializer`, `<Model>DetailSerializer`.
- [ ] `fields` explícito (List enxuta; escrita/leitura só o necessário).
- [ ] Nenhum campo sensível serializado sem `write_only`.
- [ ] Zero `SerializerMethodField` com query em listagem.
- [ ] Validações no serializer, não na view.
- [ ] `get_serializer_class` cobrindo list/retrieve/default.
- [ ] App presente em `api/serializers/__init__.py` (linha `import *`).
- [ ] `python manage.py check` OK.
