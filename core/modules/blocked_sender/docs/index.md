# BlockedSender (bloqueio antispam)

`view_name`: `blocked_sender` · papéis: `ADMIN` · base: `/api/v1/blocked-senders/`

Bloqueio por e-mail e/ou IP dos formulários públicos.

Toda resposta usa o envelope `{success, status, message, data, error}`.

| Método | URL | Permissão |
|---|---|---|
| GET | `/api/v1/blocked-senders/` | `READ` |
| POST | `/api/v1/blocked-senders/` | `CREATE` |
| GET | `/api/v1/blocked-senders/{id}/` | `READ` |
| PUT/PATCH | `/api/v1/blocked-senders/{id}/` | `UPDATE` |
| DELETE | `/api/v1/blocked-senders/{id}/` | `DELETE` |

## GET /api/v1/blocked-senders/

Query params: `search` (`email`, `ip_address`, `reason`), `is_active`,
`ordering` (`email`, `ip_address`, `is_active`, `created_at`), `page`,
`page_size`.

`data.results[]`: `id`, `email` (string, pode ser vazia), `ip_address` (ou
`null`), `reason`, `is_active`, `created_at`.

## GET /api/v1/blocked-senders/{id}/

`data`: campos da listagem + `legacy_id`, `updated_at`.

## POST /api/v1/blocked-senders/

Body: `email` e/ou `ip_address` (ao menos um; IPv4 ou IPv6), `reason`
(opcional), `is_active` (`true`).

`data`: `id`, `email`, `ip_address`, `reason`, `is_active`, `created_at`,
`updated_at`.
Erros: `400` (`error.email` quando e-mail e IP vêm vazios; IP inválido), `403`.

## PUT/PATCH /api/v1/blocked-senders/{id}/

Mesmos campos. `id`, `created_at`, `updated_at` read-only.

## DELETE /api/v1/blocked-senders/{id}/

Remoção física.
