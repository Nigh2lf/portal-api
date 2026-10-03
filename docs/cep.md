# CEP Lookup

Endpoint público para autocompletar endereço. Proxy server-side da API Noclaf.

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

> O shape exato do `data` é repassado da API Noclaf — pode variar conforme a fonte upstream.

### 400 Bad Request — CEP inválido

```json
{ "success": false, "status": 400, "message": "CEP inválido.", "error": {"detail": "..."} }
```

### 404 Not Found — CEP não encontrado

```json
{ "success": false, "status": 404, "message": "CEP não encontrado.", "error": {"detail": "..."} }
```

### 503 Service Unavailable — chave não configurada ou Noclaf fora do ar

```json
{ "success": false, "status": 503, "message": "Serviço de CEP indisponível.", "error": {"detail": "..."} }
```

## Por que server-side?

- Esconde o `NOCLAF_API_KEY` do front.
- Aplica throttle por IP (controle de custo).
- Permite trocar de provedor sem mexer no front.

## Service

[core/services/services_cep.py](../core/services/services_cep.py):

```python
from core.services import lookup_cep, normalize_cep, CepLookupError

data, error = lookup_cep("01001-000")
if error:
    # error é instância de CepLookupError com .status e .message
    ...
else:
    # data é dict
    ...
```

`lookup_cep` **nunca** levanta exceção — sempre retorna a tupla. A view apenas mapeia para o envelope HTTP.

## Exemplo de consumo no front

```js
async function buscarCep(cep) {
  const resp = await fetch(`/api/v1/cep/${cep}/`);
  const json = await resp.json();
  if (!json.success) {
    alert(json.message);
    return null;
  }
  return json.data;
}
```
