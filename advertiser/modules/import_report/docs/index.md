# Import report (relatório da importação XML)

`view_name`: `advertiser_import` · papéis: `USER`, `ADMIN` (perfil `ANUNCIANTE`,
`view_read`) · base: `/api/v1/advertiser/import-report/`

Toda resposta usa o envelope `{success, status, message, data, error}`.
Usuário sem anunciante: `404` "Usuário sem cadastro de anunciante.".

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/import-report/` | `READ` |

## GET /api/v1/advertiser/import-report/

Requer `AdvertiserIntegration` do anunciante com `xml_url` preenchida; sem
isso responde `404` com `message` = "Anunciante sem integração XML.".

`data`: `xml_url`, `last_imported_at` (`integration.last_imported_at` ou o
`finished_at` da última execução; `null` se nunca importou), `total`
(`total_properties` da última `XmlImportRun`), `valid` (`valid_properties`),
`invalid[]` (`RejectedProperty` do anunciante: `reference_code`, `reason`),
`errors[]` (`XmlImportError` da última execução, até 200, mais recentes
primeiro: `date`, `message`). Sem execução registrada, `total`/`valid` = 0 e
`errors` = `[]`.
