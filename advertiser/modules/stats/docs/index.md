# Stats (estatísticas do anunciante)

`view_name`: `advertiser_stats` · papéis: `USER`, `ADMIN` (perfil `ANUNCIANTE`,
`view_read`) · base: `/api/v1/advertiser/stats/`

Toda resposta usa o envelope `{success, status, message, data, error}`.
Usuário sem anunciante: `404` "Usuário sem cadastro de anunciante.".

Fontes: `PropertyView` (visualizações), `PropertyContactClick` (cliques em
telefone/WhatsApp), `PropertyInquiry` (mensagens) do anunciante e
`PropertyRequest` parceiro (`is_partner_broadcast`) do portal do anunciante —
estas só contam se o anunciante tem `receives_property_requests`. Agrupamento
por mês/dia em `America/Sao_Paulo`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/stats/monthly/` | `READ` |
| GET | `/api/v1/advertiser/stats/period/` | `READ` |

## GET /api/v1/advertiser/stats/monthly/

Query params: `months` (1 a 24, default `3`; inclui o mês atual).

`data[]` (do mais recente para o mais antigo): `year_month` (`"YYYY-MM"`),
`properties` (imóveis ativos hoje que já existiam ao fim do mês),
`views`, `phone_clicks`, `whatsapp_clicks`, `inquiries`, `property_requests`.

Erros: `400` (`error.months` fora da faixa).

## GET /api/v1/advertiser/stats/period/

Query params: `start`, `end` (`YYYY-MM-DD`, inclusivos). Default: do dia 1 do
mês atual até hoje.

`data`: `start`, `end`, `properties` (ativos hoje), `views`, `phone_clicks`,
`whatsapp_clicks`, `inquiries`, `property_requests`, `total_leads`
(`inquiries + phone_clicks + whatsapp_clicks + property_requests`),
`by_property[]` (`property` = UUID ou `null` se o imóvel foi apagado,
`reference_code`, `title`, `slug`, `views`, `phone_clicks`, `whatsapp_clicks`,
`inquiries`; ordenado por `views` desc, depois `inquiries`). Cliques sem
imóvel (contato do hotsite) entram nos totais mas não em `by_property`.

Erros: `400` (`error.end` quando `start > end`; datas inválidas).
