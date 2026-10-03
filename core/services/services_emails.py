"""E-mails transacionais do projeto (templates em ``core/template_emails``).

O envio em si é feito pela classe de serviço em ``core/services/email``
(provedor configurado: Brevo). Aqui ficam só os helpers de contexto e uma
função por template.
"""

from __future__ import annotations

import logging
import urllib.parse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

from .email import get_email_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def build_forgot_password_link(email: str, token: str) -> str:
    base = getattr(settings, "URL_FORGOT_PASSWORD", None)
    if not base:
        raise ImproperlyConfigured("URL_FORGOT_PASSWORD não configurada no ambiente.")
    sep = "&" if "?" in base else "?"
    return "{base}{sep}email={email}&hash={token}".format(
        base=base,
        sep=sep,
        email=urllib.parse.quote(email, safe=""),
        token=urllib.parse.quote(token, safe=""),
    )


def _resolve_logo_url() -> str:
    """Retorna a URL pública da logo do e-mail.

    Ordem de resolução:
    1. ``PublicAsset`` ativo com ``name='email_logo'`` (permite trocar pelo admin).
    2. Fallback para ``settings.EMAIL_LOGO_URL``.
    """
    try:
        from core.models import PublicAsset

        asset = PublicAsset.objects.filter(name="email_logo", is_active=True).only("image").first()
        if asset and asset.image:
            return asset.image.url
    except Exception:  # noqa: BLE001 - falhas de DB/storage nunca quebram o e-mail
        logger.debug("Falha ao resolver logo via PublicAsset; usando EMAIL_LOGO_URL.", exc_info=True)
    return getattr(settings, "EMAIL_LOGO_URL", "") or ""


def _email_context(extra: dict | None = None) -> dict:
    """Contexto compartilhado por todos os templates de e-mail."""
    ctx = {
        "logo_url": _resolve_logo_url(),
        "brand_name": getattr(settings, "EMAIL_BRAND_NAME", "") or getattr(settings, "EMAIL_SENDER_NAME", "Project"),
        "primary_color": getattr(settings, "EMAIL_PRIMARY_COLOR", "#111827"),
        "support_address": getattr(settings, "EMAIL_SUPPORT_ADDRESS", "") or getattr(settings, "EMAIL_SENDER_ADDRESS", ""),
    }
    if extra:
        ctx.update(extra)
    return ctx


def send_template_email(*, to_email: str, to_name: str | None, subject: str, template: str, context: dict | None = None, reply_to: str = "", tags: list[str] | None = None) -> bool:
    """
    Renderiza um template de ``core/template_emails`` e envia pelo serviço configurado

    Args:
        to_email: destinatário
        to_name: nome do destinatário (opcional)
        subject: assunto
        template: nome do template (ex.: ``welcome.html``)
        context: variáveis extras do template
        reply_to: e-mail de resposta (ex.: o visitante que mandou a mensagem)
        tags: etiquetas para o painel do provedor

    Returns:
        True se o provedor aceitou o envio; nunca levanta
    """
    html = render_to_string(template, _email_context(context))
    return get_email_service().send_html(to_email=to_email, to_name=to_name or "", subject=subject, html_content=html, reply_to=reply_to, tags=tags)


# ---------------------------------------------------------------------------
# Funções públicas (uma por template)
# ---------------------------------------------------------------------------
def send_email_forgot_password(email: str, name: str | None, token: str) -> bool:
    """Envia o e-mail de reset de senha. Recebe o token, monta a URL aqui."""
    link = build_forgot_password_link(email, token)
    return send_template_email(
        to_email=email,
        to_name=name,
        subject="Redefinir senha",
        template="forgot_password.html",
        context={"name": name or "", "link": link},
        tags=["forgot_password"],
    )


def send_email_welcome(email: str, name: str | None) -> bool:
    """E-mail de boas-vindas pós cadastro."""
    return send_template_email(
        to_email=email,
        to_name=name,
        subject=f"Bem-vindo(a) à {getattr(settings, 'EMAIL_BRAND_NAME', 'Project')}!",
        template="welcome.html",
        context={"name": name or ""},
        tags=["welcome"],
    )


def send_email_verification_code(email: str, name: str | None, code: str) -> bool:
    """E-mail de confirmação de cadastro com código numérico."""
    return send_template_email(
        to_email=email,
        to_name=name,
        subject="Confirme seu e-mail",
        template="verify_email.html",
        context={"name": name or "", "code": code},
        tags=["verify_email"],
    )
