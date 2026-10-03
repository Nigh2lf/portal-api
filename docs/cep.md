# CEP Lookup

Endpoint público para autocompletar endereço. Consulta a **ViaCEP** e grava o
resultado na tabela `PostalCode` (`core.PostalCode`): a segunda consulta do
mesmo CEP não sai do banco. CEPs inexistentes também são gravados
(`not_found=True`) para não reconsultar.

## Endpoint

```
GET /api/v1/cep/<cep>/
```

- **Auth**: pública (`AllowAny`).
- **Throttle**: scope `cep` (default `60/hour` por IP, configurável via `THROTTLE_CEP`).
- Aceita CEP com ou sem formatação: `01001000`, `01001-000`, `01001 000`.

## Respostas

### 200 OK

```json
{
  "success": true,
  "status": 200,
  "message": "",
  "data": {
    "cep": "01001-000",
    "logradouro": "Praça da Sé",
    "bairro": "Sé",
    "cidade": "São Paulo",
    "uf": "SP"
  },
  "error": null
}
```

### Erros

| Status | Quando |
|---|---|
| 400 | CEP com menos/mais de 8 dígitos |
| 404 | ViaCEP respondeu `{"erro": true}` |
| 502 | Resposta inválida da ViaCEP |
| 503 | ViaCEP indisponível (timeout/rede) |

## Configuração

| Variável | Default | Descrição |
|---|---|---|
| `VIACEP_URL` | `https://viacep.com.br/ws/{cep}/json/` | URL com placeholder `{cep}` |
| `CEP_API_TIMEOUT` | `10` | Timeout em segundos |
| `CEP_CACHE_DAYS` | `365` | Idade máxima do cache; `0` = nunca expira |

## Uso server-side

```python
from core.services import lookup_cep

data, error = lookup_cep("01310-100")
if error:
    ...  # error.status / error.message
```
