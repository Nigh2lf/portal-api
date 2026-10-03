"""Envio de e-mail transacional por classe de serviço.

Provedor escolhido por ``settings.EMAIL_PROVIDER`` (hoje: ``brevo``). Toda
chamada passa por :func:`get_email_service`, que devolve uma instância de
:class:`EmailService`; o restante do projeto nunca fala com a API do provedor
diretamente.
"""

from __future__ import annotations

from django.conf import settings

from .base import EmailMessage, EmailService, NullEmailService
from .brevo import BrevoEmailService

__all__ = ["EmailMessage", "EmailService", "NullEmailService", "BrevoEmailService", "get_email_service"]


def get_email_service() -> EmailService:
    """
    Instancia o serviço de e-mail configurado

    Returns:
        EmailService pronto para `send()`; sem chave configurada, um serviço nulo que só loga
    """
    provider = (getattr(settings, "EMAIL_PROVIDER", "brevo") or "brevo").lower()
    if provider == "brevo" and getattr(settings, "BREVO_API_KEY", ""):
        return BrevoEmailService(
            api_key=settings.BREVO_API_KEY,
            api_url=getattr(settings, "BREVO_API_URL", BrevoEmailService.DEFAULT_URL),
            sender_name=getattr(settings, "EMAIL_SENDER_NAME", "Portal"),
            sender_email=getattr(settings, "EMAIL_SENDER_ADDRESS", "no-reply@example.com"),
            timeout=int(getattr(settings, "EMAIL_API_TIMEOUT", 10)),
        )
    return NullEmailService()
