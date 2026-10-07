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

Query params: `search` (`advertiser__name`), `advertiser` (UUID),
`report_email_sent`, `started_at__gte`, `started_at__lte` (datetime ISO),
`ordering` (`started_at`, `finished_at`, `total_properties`,
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

## Importar agora / simular (app `importacao`)

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
