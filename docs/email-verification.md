# Verificação de E-mail

Fluxo opcional de confirmação de e-mail por código de 6 dígitos.

## Ativar

```bash
EMAIL_VERIFICATION_REQUIRED=True
EMAIL_VERIFICATION_CODE_TTL_MIN=30
```

Quando `EMAIL_VERIFICATION_REQUIRED=False` (default), o cadastro envia o **welcome e-mail** padrão e o usuário já entra com `email_verified=False` (mas sem bloqueio). Os endpoints `send-verification-code` e `verify-email` ficam **desativados** (retornam `404`).

Quando `True`:
- Cadastro (`POST /users/`) gera código e envia e-mail de verificação no lugar do welcome.
- Endpoints abaixo passam a responder normalmente.

## Endpoints

Sob `/api/v1/users/`. Todos públicos, throttle `forgot_password` (5/h por padrão).

| Método | Path | Body | Comportamento |
|---|---|---|---|
| POST | `/` | `{email, password, name}` | Cadastra. Se a flag está ativa, envia código; senão, welcome. |
| POST | `/send-verification-code/` | `{email}` | Reenvia (ou gera) código. Resposta sempre genérica. **404 se a flag estiver desligada.** |
| POST | `/verify-email/` | `{email, code}` | Marca `email_verified=True` se código bate e não expirou. Resposta sempre genérica. **404 se a flag estiver desligada.** |

> **Anti-enumeração**: `send-verification-code` e `verify-email` retornam sempre o mesmo envelope de sucesso, mesmo que o email não exista, esteja já verificado ou o código esteja errado. Detalhes vão para o log do servidor.

## Helpers no model

```python
user.generate_email_verification_code()
# - Gera código 6 dígitos com secrets.randbelow
# - Define email_verification_expire = now + EMAIL_VERIFICATION_CODE_TTL_MIN
# - Salva e retorna o código (use para enviar por e-mail)

user.confirm_email_verification("123456")
# - Compara via secrets.compare_digest (timing-safe)
# - Checa expiração
# - Em sucesso: email_verified=True, limpa code/expire, salva
# - Retorna bool
```

## Bloquear ações de usuários não verificados

Não há permission pronta — o boilerplate deixa intencionalmente como decisão de produto. Se quiser, adicione:

```python
from rest_framework.permissions import BasePermission

class IsEmailVerified(BasePermission):
    message = "E-mail não verificado."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.email_verified
        )
```

E inclua nas views sensíveis:

```python
permission_classes = [IsAuthenticated, IsEmailVerified]
```

## Template

[core/template_emails/verify_email.html](../core/template_emails/verify_email.html). Usa a classe `.code-box` do `_base.html` (centralizada, fonte monospace, dark mode-safe).

Para customizar, ver [emails.md](emails.md#customizar-visual-rapidamente).
