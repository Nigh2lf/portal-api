"""Serviço de envio de e-mails transacionais via API da Noclaf.

Endpoint: ``POST {NOCLAF_EMAIL_API_URL}`` (default
``https://emails.noclaf.com.br/core/send-html-email/``)
Autenticação: header ``X-Api-Key`` com UUID configurado em
``NOCLAF_EMAIL_API_KEY``.

Templates Django são renderizados localmente (com a logo pública injetada via
``EMAIL_LOGO_URL``) e enviados como ``html_content`` para a Noclaf.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

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
        logger.debug(
            "Falha ao resolver logo via PublicAsset; usando EMAIL_LOGO_URL.", exc_info=True
        )
    return getattr(settings, "EMAIL_LOGO_URL", "") or ""


def _email_context(extra: dict | None = None) -> dict:
    """Contexto compartilhado por todos os templates de e-mail."""
    ctx = {
        "logo_url": _resolve_logo_url(),
        "brand_name": getattr(settings, "EMAIL_BRAND_NAME", "")
        or getattr(settings, "EMAIL_SENDER_NAME", "Project"),
        "primary_color": getattr(settings, "EMAIL_PRIMARY_COLOR", "#111827"),
        "support_address": getattr(settings, "EMAIL_SUPPORT_ADDRESS", "")
        or getattr(settings, "EMAIL_SENDER_ADDRESS", ""),
    }
    if extra:
        ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# Cliente HTTP da Noclaf
# ---------------------------------------------------------------------------
def _noclaf_send(
    *,
    to_email: str,
    to_name: str | None,
    subject: str,
    html_content: str,
) -> bool:
    """POST → endpoint Noclaf. Retorna True/False, nunca levanta."""

    api_url = getattr(settings, "NOCLAF_EMAIL_API_URL", "")
    api_key = getattr(settings, "NOCLAF_EMAIL_API_KEY", "")
    if not api_url or not api_key:
        logger.warning(
            "NOCLAF_EMAIL_API_URL/NOCLAF_EMAIL_API_KEY não configurados; e-mail não enviado."
        )
        return False

    payload = {
        "to_email": to_email,
        "to_name": to_name or "",
        "subject": subject,
        "html_content": html_content,
        "sender_name": getattr(settings, "EMAIL_SENDER_NAME", "Project"),
        "sender_email": getattr(settings, "EMAIL_SENDER_ADDRESS", "no-reply@example.com"),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 - URL controlada via settings
        api_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": api_key,
        },
    )
    timeout = getattr(settings, "NOCLAF_EMAIL_TIMEOUT", 10)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read()
            try:
                parsed = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                parsed = {"raw": body[:200].decode("utf-8", errors="replace")}
            if 200 <= resp.status < 300 and parsed.get("worked", True):
                return True
            logger.error("Noclaf email API rejeitou envio: status=%s body=%s", resp.status, parsed)
            return False
    except HTTPError as e:
        logger.error("Noclaf email API HTTPError %s: %s", e.code, e.reason)
        return False
    except (URLError, TimeoutError) as e:
        logger.error("Noclaf email API indisponível: %s", e)
        return False
    except Exception:  # noqa: BLE001 - nunca quebrar fluxo de negócio por causa de e-mail
        logger.exception("Falha inesperada ao enviar e-mail via Noclaf.")
        return False


# ---------------------------------------------------------------------------
# Funções públicas (uma por template)
# ---------------------------------------------------------------------------
def send_email_forgot_password(email: str, name: str | None, token: str) -> bool:
    """Envia o e-mail de reset de senha. Recebe o token, monta a URL aqui."""
    link = build_forgot_password_link(email, token)
    html = render_to_string(
        "forgot_password.html",
        _email_context({"name": name or "", "link": link}),
    )
    return _noclaf_send(
        to_email=email,
        to_name=name,
        subject="Redefinir senha",
        html_content=html,
    )


def send_email_welcome(email: str, name: str | None) -> bool:
    """E-mail de boas-vindas pós cadastro."""
    html = render_to_string(
        "welcome.html",
        _email_context({"name": name or ""}),
    )
    return _noclaf_send(
        to_email=email,
        to_name=name,
        subject=f"Bem-vindo(a) à {getattr(settings, 'EMAIL_BRAND_NAME', 'Project')}!",
        html_content=html,
    )


def send_email_verification_code(email: str, name: str | None, code: str) -> bool:
    """E-mail de confirmação de cadastro com código numérico."""
    html = render_to_string(
        "verify_email.html",
        _email_context({"name": name or "", "code": code}),
    )
    return _noclaf_send(
        to_email=email,
        to_name=name,
        subject="Confirme seu e-mail",
        html_content=html,
    )
