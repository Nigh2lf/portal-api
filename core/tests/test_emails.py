"""Cliente de e-mail (Noclaf): comportamento sem API key."""

from __future__ import annotations

from core.services import send_email_welcome


def test_send_email_welcome_is_noop_without_api_key(settings) -> None:
    settings.NOCLAF_EMAIL_API_KEY = ""
    assert send_email_welcome("a@b.com", "Alice") is False
