# ContactMessage (fale conosco)

`view_name`: `contact_message` · papéis: `ADMIN` · base: `/api/v1/contact-messages/`

Somente leitura e exclusão (`POST`/`PUT`/`PATCH` → `405`).

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/contact-messages/` | `READ` |
| GET | `/api/v1/contact-messages/{id}/` | `READ` |
| DELETE | `/api/v1/contact-messages/{id}/` | `DELETE` |

## GET /api/v1/contact-messages/

Query params: `search` (`name`, `email`, `phone`, `subject`, `message`),
`portal` (UUID), `created_at__gte`, `created_at__lte` (datetime ISO),
`ordering` (`name`, `email`, `subject`, `created_at`), `page`, `page_size`.

`data.results[]`: `id`, `name`, `email`, `phone`, `subject`, `portal` (UUID),
`portal_name`, `created_at`.

## GET /api/v1/contact-messages/{id}/

`data`: campos da listagem + `message`, `ip_address`, `legacy_id`,
`updated_at`.

## DELETE /api/v1/contact-messages/{id}/

Remoção física. Resposta `204`.
