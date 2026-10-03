"""Testes dos signals em ``core.signals_audit`` -> ``LogModelChange``."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from core import signals_audit
from core.middleware.current_user import set_current_user
from core.models import LogModelChange

User = get_user_model()


@pytest.fixture
def audit_on(db):
    """Conecta os signals de auditoria para core.User durante o teste."""
    with override_settings(MODEL_AUDIT_ENABLED=True, MODEL_AUDIT_MODELS="core.User"):
        signals_audit.connect()
        yield
        # Desconecta para não contaminar outros testes
        from django.db.models.signals import post_delete, post_save, pre_save

        for label in ("core.User",):
            pre_save.disconnect(dispatch_uid=f"audit_pre_{label}")
            post_save.disconnect(dispatch_uid=f"audit_post_{label}")
            post_delete.disconnect(dispatch_uid=f"audit_del_{label}")
        set_current_user(None)


def test_create_user_emits_create_log_with_redacted_password(audit_on):
    user = User.objects.create_user(email="alice@example.com", password="Strong#Pass1234")

    log = LogModelChange.objects.get(object_id=str(user.pk), action=LogModelChange.Action.CREATE)
    assert log.app_label == "core"
    assert log.model_name == "User"
    new_state = log.changes["new"]
    assert new_state["email"] == "alice@example.com"
    assert new_state["password"] == "<redacted>"


def test_update_user_emits_diff_without_password_value(audit_on):
    user = User.objects.create_user(email="bob@example.com", password="Strong#Pass1234")
    LogModelChange.objects.filter(object_id=str(user.pk)).delete()

    user.name = "Bob"
    user.set_password("Another#Pass5678")
    user.save()

    log = LogModelChange.objects.get(object_id=str(user.pk), action=LogModelChange.Action.UPDATE)
    diff = log.changes
    assert "name" in diff
    assert diff["name"]["new"] == "Bob"
    # `password` é redatado em ambos lados, então `old == new == "<redacted>"`
    # e o diff omite o campo (correto) — mas o valor real nunca aparece.
    if "password" in diff:
        assert diff["password"]["old"] == "<redacted>"
        assert diff["password"]["new"] == "<redacted>"
    # Garantia forte: nenhum hash de senha vaza no JSON do log
    import json

    serialized = json.dumps(diff)
    assert "Another#Pass5678" not in serialized
    assert "pbkdf2_" not in serialized


def test_actor_is_recorded_when_set(audit_on, admin_user):
    set_current_user(admin_user)
    try:
        user = User.objects.create_user(email="carol@example.com", password="Strong#Pass1234")
    finally:
        set_current_user(None)

    log = LogModelChange.objects.get(object_id=str(user.pk), action=LogModelChange.Action.CREATE)
    assert log.actor_id == admin_user.id
    assert log.actor_email == admin_user.email


def test_log_tables_themselves_are_never_audited(audit_on):
    """Importar e criar LogRequest/LogModelChange direto NÃO gera novo audit log."""
    from core.models import LogRequest

    LogRequest.objects.create(method="GET", path="/x", ip="127.0.0.1")
    # Nenhum log adicional referente a LogRequest foi criado
    assert not LogModelChange.objects.filter(model_name="LogRequest").exists()
    assert not LogModelChange.objects.filter(model_name="LogModelChange").exists()


@pytest.mark.django_db
def test_signals_disabled_writes_nothing():
    """Sem MODEL_AUDIT_ENABLED, nenhum log é gerado."""
    User.objects.create_user(email="dave@example.com", password="Strong#Pass1234")
    assert LogModelChange.objects.count() == 0
