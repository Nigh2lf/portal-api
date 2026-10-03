# E-mails Transacionais

Cliente Noclaf, templates compatíveis cross-client e como customizar.

## Como funciona

```
core.services.send_email_*  ──renderiza template──>  HTML
                            ──POST X-Api-Key──>  https://emails.noclaf.com.br/core/send-html-email/
```

- Cliente HTTP em [core/services/services_emails.py](../core/services/services_emails.py) usa `urllib.request` (zero deps).
- Falhas (timeout, 5xx, key ausente) são **logadas e suprimidas**. **Não** quebram o fluxo de negócio.

## Configuração

Ver [configuration.md](configuration.md#api-noclaf-e-mails--cep) e [configuration.md](configuration.md#e-mails-templates--branding).

Mínimo:
```bash
NOCLAF_API_KEY=<uuid-fornecido-pela-noclaf>
EMAIL_SENDER_NAME=MeuApp
EMAIL_SENDER_ADDRESS=no-reply@meuapp.com
EMAIL_SUPPORT_ADDRESS=suporte@meuapp.com
```

## Funções públicas

```python
from core.services import (
    send_email_forgot_password,
    send_email_welcome,
    send_email_verification_code,
)

send_email_welcome("user@x.com", "Maria")
send_email_forgot_password("user@x.com", "Maria", token="...")
send_email_verification_code("user@x.com", "Maria", code="123456")
```

Todas retornam `bool` (True = aceito pela Noclaf).

## Templates

Em [core/template_emails/](../core/template_emails/):

| Arquivo | Quando |
|---|---|
| `_base.html` | Layout compartilhado (header com logo, footer, dark mode). |
| `welcome.html` | Pós cadastro. |
| `forgot_password.html` | Reset de senha (botão CTA + fallback link). |
| `verify_email.html` | Código de 6 dígitos. |

Todos estendem `_base.html` via `{% extends "_base.html" %}`. Para criar um template novo:

```html
{% extends "_base.html" %}

{% block content %}
  <h1 class="h1 text-strong" style="margin:0 0 12px;font-size:22px;color:#0f172a;">Título</h1>
  <p class="text-body" style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#1f2937;">
    Olá <strong>{{ name }}</strong>, ...
  </p>
{% endblock %}
```

> Use as classes `text-strong`, `text-body`, `text-muted`, `bg-card`, `border-soft`, `code-box` para que o dark mode funcione automaticamente.

## Logo

A logo do header é resolvida nesta ordem:

1. **`PublicAsset` ativo com `name="email_logo"`** — cadastre em `/admin/core/publicasset/add/`.
2. Fallback `EMAIL_LOGO_URL` (env).
3. Se nenhum dos dois: o header mostra `EMAIL_BRAND_NAME` em texto.

> Vantagem do `PublicAsset`: troca a logo sem redeploy. Em S3, o `PublicMediaStorage` gera URL pública direta (sem querystring) e o acesso vem da bucket policy do prefixo `public/`, então a URL serve direto em qualquer cliente de e-mail.

Detalhes: [public-assets.md](public-assets.md).

## Compatibilidade cross-client

O `_base.html` foi feito para funcionar em:

| Cliente | Notas |
|---|---|
| Gmail (web/iOS/Android) | Estilos críticos duplicados inline; classes do `<style>` funcionam para dark mode. |
| Apple Mail (macOS/iOS) | `prefers-color-scheme` ativo; `meta color-scheme` previne color-shift; override de auto-link de telefone/data. |
| Outlook desktop (Win) | Botão renderizado como **VML** (`<v:roundrect>`) dentro de `<!--[if mso]>`; `<o:AllowPNG/>` força renderização decente da logo. |
| Outlook.com / Office 365 | Dark mode via prefixo `[data-ogsc]`. |
| iCloud Mail, Yahoo, Thunderbird | Tabela + inline garante layout consistente. |

### Mobile

`@media (max-width:600px)` ajusta:
- Container vai a 100% de largura.
- Padding lateral reduz para 20px.
- Botão de ação vira full-width.
- Caixa de código (`.code-box`) reduz `font-size` e `letter-spacing`.

### Dark mode

Suporte via duas estratégias combinadas:

```css
@media (prefers-color-scheme: dark) { /* Apple Mail, iOS, Outlook mobile, Thunderbird */ }
[data-ogsc] { /* Outlook.com / Office 365 */ }
```

Não use cores hardcoded em templates filhos sem dar uma classe `text-*`. Senão, no dark mode vai ficar texto preto em fundo escuro.

## Testar localmente sem mandar e-mail

Os testes do boilerplate fazem isso (`override_settings(NOCLAF_API_KEY="")`). O service detecta key ausente, loga warning e retorna `False` — não tenta acessar a rede.

## Customizar visual rapidamente

| Quero mudar... | Onde |
|---|---|
| Cor primária dos botões | `EMAIL_PRIMARY_COLOR` |
| Logo | `PublicAsset(name="email_logo")` ou `EMAIL_LOGO_URL` |
| Nome da marca | `EMAIL_BRAND_NAME` |
| E-mail de suporte no footer | `EMAIL_SUPPORT_ADDRESS` |
| Layout (header/footer) | `core/template_emails/_base.html` |
| Conteúdo de um template | `core/template_emails/<nome>.html` |
