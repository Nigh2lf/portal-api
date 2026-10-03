"""Brevo (ex-Sendinblue) — API transacional ``POST /v3/smtp/email``.

Documentação: https://developers.brevo.com/reference/sendtransacemail
Autenticação: header ``api-key``.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from urllib.error import HTTPError, URLError

from .base import EmailMessage, EmailService

logger = logging.getLogger(__name__)


class BrevoEmailService(EmailService):
    DEFAULT_URL = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, *, api_key: str, sender_name: str, sender_email: str, api_url: str = DEFAULT_URL, timeout: int = 10):
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_URL
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.timeout = timeout

    def build_payload(self, message: EmailMessage) -> dict:
        """Monta o corpo no formato da Brevo."""
        payload: dict = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": message.to_email, **({"name": message.to_name} if message.to_name else {})}],
            "subject": message.subject,
            "htmlContent": message.html_content,
        }
        if message.text_content:
            payload["textContent"] = message.text_content
        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to}
        if message.cc:
            payload["cc"] = [{"email": e} for e in message.cc]
        if message.tags:
            payload["tags"] = message.tags
        return payload

    def send(self, message: EmailMessage) -> bool:
        data = json.dumps(self.build_payload(message)).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 - URL fixa da Brevo (ou settings)
            self.api_url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "api-key": self.api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                if 200 <= resp.status < 300:
                    return True
                logger.error("Brevo rejeitou o envio: status=%s", resp.status)
                return False
        except HTTPError as e:
            detalhe = ""
            try:
                detalhe = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:  # noqa: BLE001, S110 - corpo opcional
                pass
            logger.error("Brevo HTTPError %s: %s %s", e.code, e.reason, detalhe)
            return False
        except (URLError, TimeoutError) as e:
            logger.error("Brevo indisponível: %s", e)
            return False
        except Exception:  # noqa: BLE001 - e-mail nunca derruba o fluxo de negócio
            logger.exception("Falha inesperada ao enviar e-mail via Brevo.")
            return False
