from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    html_content: str
    to_name: str = ""
    text_content: str = ""
    reply_to: str = ""
    cc: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class EmailService(ABC):
    """Contrato de envio: implementações nunca levantam; devolvem True/False e logam."""

    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """
        Envia a mensagem

        Args:
            message: destinatário, assunto e conteúdo

        Returns:
            True se o provedor aceitou o envio
        """

    def send_html(self, *, to_email: str, subject: str, html_content: str, to_name: str = "", reply_to: str = "", tags: list[str] | None = None) -> bool:
        return self.send(EmailMessage(to_email=to_email, to_name=to_name, subject=subject, html_content=html_content, reply_to=reply_to, tags=tags or []))


class NullEmailService(EmailService):
    """Usado sem chave configurada (dev/testes): não envia, só registra no log."""

    def send(self, message: EmailMessage) -> bool:
        logger.warning("E-mail não enviado (provedor não configurado): para=%s assunto=%s", message.to_email, message.subject)
        return False
