# E-mails transacionais

O envio é feito por uma **classe de serviço** em `core/services/email/`:

- `EmailService` (abstrato) — contrato `send(EmailMessage) -> bool`. Nunca levanta.
- `BrevoEmailService` — provedor atual, API `POST https://api.brevo.com/v3/smtp/email`
  (header `api-key`).
- `NullEmailService` — usado quando `BREVO_API_KEY` está vazia: só loga.
- `get_email_service()` — fábrica que lê `EMAIL_PROVIDER` / `BREVO_API_KEY`.

Ninguém fora desse pacote fala com a API da Brevo. Os templates e as funções
por tipo de e-mail ficam em `core/services/services_emails.py`:

```python
from core.services import send_email_welcome
from core.services.services_emails import send_template_email

send_email_welcome(user.email, user.name)
send_template_email(
    to_email="anunciante@x.com",
    to_name="Imobiliária X",
    subject="Nova mensagem sobre o imóvel 123",
    template="lead_property.html",
    context={"name": "...", "message": "..."},
    reply_to="visitante@y.com",
    tags=["lead"],
)
```

## Configuração

| Variável | Descrição |
|---|---|
| `EMAIL_PROVIDER` | `brevo` (único hoje) |
| `BREVO_API_KEY` | Chave da API transacional da Brevo (obrigatória em produção: check `core.W003`) |
| `BREVO_API_URL` | Default `https://api.brevo.com/v3/smtp/email` |
| `EMAIL_API_TIMEOUT` | Timeout em segundos (default 10) |
| `EMAIL_SENDER_NAME` / `EMAIL_SENDER_ADDRESS` | Remetente (precisa estar validado na Brevo) |
| `EMAIL_BRAND_NAME`, `EMAIL_PRIMARY_COLOR`, `EMAIL_SUPPORT_ADDRESS`, `EMAIL_LOGO_URL` | Branding dos templates |

## Templates

Ficam em `core/template_emails/` e herdam `_base.html` (logo, cor primária,
dark mode, Outlook). A logo vem de um `PublicAsset` ativo com `name="email_logo"`
ou, na falta dele, de `EMAIL_LOGO_URL`.

## Testes

`core/tests/test_emails.py` cobre a fábrica, o payload da Brevo e a falha
silenciosa. Em testes, deixe `BREVO_API_KEY` vazia para cair no
`NullEmailService`.
