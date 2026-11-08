# XmlImportRun (execução da importação XML)

`view_name`: `xml_import_run` · papéis: `ADMIN` · base: `/api/v1/xml-import-runs/`

Somente leitura e exclusão (`POST`/`PUT`/`PATCH` → `405`). Registros são
gravados pelo job de importação.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/xml-import-runs/` | `READ` |
| GET | `/api/v1/xml-import-runs/{id}/` | `READ` |
| DELETE | `/api/v1/xml-import-runs/{id}/` | `DELETE` |

## GET /api/v1/xml-import-runs/

Query params: `search` (`advertiser__name`), `advertiser` (UUID), `batch` (UUID),
`batch__isnull`, `status`,
`report_email_sent`, `started_at__gte`, `started_at__lte` (datetime ISO),
`ordering` (`advertiser__name`, `started_at`, `finished_at`, `total_properties`, `valid_properties`,
`invalid_properties`), `page`, `page_size`.

`data.results[]`: `id`, `advertiser` (UUID), `advertiser_name`, `started_at`,
`finished_at` (ou `null` se em andamento), `total_properties`,
`valid_properties`, `invalid_properties`, `report_email_sent`, `created_at`.

## GET /api/v1/xml-import-runs/{id}/

`data`: campos da listagem + `errors[]` (`id`, `property_reference_code`,
`message`, `payload`, `created_at`; ordenados por `created_at`), `legacy_id`,
`updated_at`.

## DELETE /api/v1/xml-import-runs/{id}/

Remoção física; os erros vinculados ficam com `run = null`. Resposta `204`.

## Importar agora / simular (app `xml_import`)

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/xml-import-runs/advertisers/` | `READ` |
| POST | `/api/v1/xml-import-runs/run/` | `CREATE` |
| GET | `/api/v1/xml-import-runs/simulation/?advertiser=<uuid>` | `READ` |

`POST /xml-import-runs/` (criação direta) responde `405`.

### GET /api/v1/xml-import-runs/advertisers/

Anunciantes publicados com integração XML ativa. `data[]`: `id`, `name`,
`legacy_id`, `integrator` (nome ou `null`), `xml_url`, `last_imported_at`.

### POST /api/v1/xml-import-runs/run/

Body: `advertiser` (UUID), `simulate` (bool, padrão `false`). Dispara em
segundo plano o download, a normalização e a comparação com o banco; responde
`202` com `{started: true}` sem esperar. Importação real cria uma execução na
listagem (com `finished_at` nulo enquanto roda). Simulação não grava nada no
banco: o resultado fica disponível em `GET .../simulation/`.

Erros: `400` (`advertiser` sem XML ativo), `409` (já há importação ou simulação
rodando para o anunciante).

### GET /api/v1/xml-import-runs/simulation/?advertiser=<uuid>

Resultado da última simulação. `data`: `running` (bool, se ainda está
rodando), `gerado_em`, `formato`, `baixado_em`, `total_feed`, `novos`,
`alterados`, `iguais`, `excluidos`, `ignorados` (contagens) e as listas
`codigos_novos[]`, `codigos_alterados[]` (`{codigo, campos[]}`),
`codigos_excluidos[]` e `ignorados_lista[]` (`{codigo, motivo}`), até 500 itens
cada. Se a simulação falhou (download, formato, feed vazio): `{erro, gerado_em}`.
`404` se nunca houve simulação.

## Lotes (`/api/v1/xml-import-runs/batches/`)

Toda importação (cron, comando ou painel) é um lote (`XmlImportBatch`) com uma
execução por anunciante. Execuções sem lote (`?batch__isnull=true` na listagem
acima) são o histórico do sistema antigo e as rodadas de um anunciante pelo
comando `import_xml --advertiser`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/xml-import-runs/batches/` | `READ` |
| POST | `/api/v1/xml-import-runs/batches/` | `CREATE` |
| GET | `/api/v1/xml-import-runs/batches/active/` | `READ` |
| GET | `/api/v1/xml-import-runs/batches/{id}/` | `READ` |
| POST | `/api/v1/xml-import-runs/batches/{id}/cancel/` | `CREATE` |

### GET /api/v1/xml-import-runs/batches/

Paginado (`page`, `page_size`), mais recente primeiro. Filtros: `status`,
`origin` (`MANUAL`, `CRON`, `COMMAND`), `scope` (`ALL`, `SELECTED`),
`created_at__gte`, `created_at__lte`, `advertiser` (UUID) e `search` (nome do
anunciante); os dois últimos trazem os lotes em que o anunciante rodou.
`ordering`: `created_at`, `started_at`, `finished_at`, `total_advertisers`,
`failed` (com `-` para decrescente).

`data.results[]`: `id`, `status`, `origin`, `scope`, `total_advertisers`,
`done`, `ok`, `failed`, `skipped`, `cancelled`, `current_advertiser`,
`current_advertiser_name`, `created_by`, `created_by_name`, `deadline_at`,
`started_at`, `finished_at`, `heartbeat_at`, `error_message`, `created_at` e a
soma dos imóveis das execuções: `total_properties`, `valid_properties`,
`invalid_properties`.

### GET /api/v1/xml-import-runs/batches/{id}/ e `.../active/`

Campos da listagem + `runs[]` (execuções já feitas, na ordem em que rodaram) e
`pending[]` (`{id, name}` dos anunciantes que ainda vão rodar). `active/`
devolve `null` se nenhum lote está na fila ou em execução.

O detalhe de uma execução (`GET /xml-import-runs/{id}/`) traz `batch` e
`batch_started_at` para o painel voltar ao lote.
