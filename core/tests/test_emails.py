from core.services.email import BrevoEmailService, EmailMessage, NullEmailService, get_email_service


def test_sem_chave_usa_servico_nulo(settings):
    settings.BREVO_API_KEY = ""
    assert isinstance(get_email_service(), NullEmailService)
    assert get_email_service().send_html(to_email="a@a.com", subject="x", html_content="<p>x</p>") is False


def test_com_chave_usa_brevo(settings):
    settings.BREVO_API_KEY = "chave"
    settings.EMAIL_SENDER_NAME = "Portal"
    settings.EMAIL_SENDER_ADDRESS = "no-reply@portal.com"
    service = get_email_service()
    assert isinstance(service, BrevoEmailService)
    payload = service.build_payload(EmailMessage(to_email="a@a.com", to_name="Ana", subject="Oi", html_content="<p>oi</p>", reply_to="v@v.com", tags=["t"]))
    assert payload["sender"] == {"name": "Portal", "email": "no-reply@portal.com"}
    assert payload["to"] == [{"email": "a@a.com", "name": "Ana"}]
    assert payload["htmlContent"] == "<p>oi</p>"
    assert payload["replyTo"] == {"email": "v@v.com"}
    assert payload["tags"] == ["t"]


def test_brevo_falha_nao_levanta(mocker):
    service = BrevoEmailService(api_key="k", sender_name="P", sender_email="p@p.com")
    mocker.patch("core.services.email.brevo.urllib.request.urlopen", side_effect=OSError("down"))
    assert service.send(EmailMessage(to_email="a@a.com", subject="x", html_content="x")) is False
