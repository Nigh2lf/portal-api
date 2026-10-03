# Inquiry (ofertas/mensagens recebidas pelo anunciante)

`view_name`: `advertiser_inquiry` · papéis: `USER`, `ADMIN` (perfil `ANUNCIANTE`,
`view_read`) · base: `/api/v1/advertiser/inquiries/` · somente leitura

Toda resposta usa o envelope `{success, status, message, data, error}` (exceto
o CSV). Só mensagens cujo `advertiser` é o da sessão. Usuário sem anunciante:
`404` "Usuário sem cadastro de anunciante.".

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/advertiser/inquiries/` | `READ` |
| GET | `/api/v1/advertiser/inquiries/{id}/` | `READ` |
| GET | `/api/v1/advertiser/inquiries/export/` | `READ` |

## GET /api/v1/advertiser/inquiries/

Query params: `created_at__gte`, `created_at__lte` (ISO 8601; data pura é
interpretada como 00:00, então para incluir o dia final envie
`YYYY-MM-DDT23:59:59`), `search` (`name`, `email`, `phone`,
`property_reference_code`, `message`), `ordering` (`name`, `email`,
`created_at`; default `-created_at`), `page`, `page_size`.

`data.results[]`: `id`, `property` (UUID ou `null` se o imóvel foi apagado),
`property_reference_code`, `property_title`, `property_slug` (`null` sem
imóvel), `portal_slug`, `name`, `email`, `phone`, `message`,
`contact_preferences` (lista, ex.: `["WHATSAPP", "EMAIL"]`), `is_mobile`,
`created_at`.

## GET /api/v1/advertiser/inquiries/{id}/

`data`: mesmo objeto da listagem.

## GET /api/v1/advertiser/inquiries/export/

Mesmos filtros da listagem (`created_at__gte`, `created_at__lte`, `search`).
Resposta **sem envelope**: `text/csv; charset=utf-8` com BOM, separador `;`,
`Content-Disposition: attachment; filename="ofertas.csv"`.

Colunas: Data (`dd/mm/aaaa hh:mm`, horário local), Nome, E-mail, Telefone,
Código do imóvel, Imóvel (título), Mensagem, Preferência de contato, Celular
(`Sim`/`Não`).
