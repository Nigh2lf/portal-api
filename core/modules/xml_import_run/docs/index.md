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
