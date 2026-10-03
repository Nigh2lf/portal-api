"""Signals de auditoria — populam ``LogModelChange`` em CREATE/UPDATE/DELETE.

Quais models entram na auditoria? Definido pela env ``MODEL_AUDIT_MODELS``
(csv ``app_label.ModelName``). Default: ``core.User``.

Implementação:

- ``pre_save``: se o objeto já existe, busca o estado anterior do banco e
  guarda como atributo temporário. Se for novo, marca como CREATE.
- ``post_save``: emite log com action CREATE ou UPDATE (com diff campo a campo).
- ``post_delete``: emite log DELETE.

Campos sensíveis (``password``, ``forgot_password_hash``,
``email_verification_code``, etc.) **nunca** têm valor gravado — apenas
``"<changed>"``.

Para evitar loops infinitos, o próprio ``LogModelChange`` é ignorado.
"""

from __future__ import annotations

import logging

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save

from core.middleware.current_user import get_current_user

logger = logging.getLogger(__name__)

_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "forgot_password_hash",
        "forgot_password_expire",
        "email_verification_code",
        "email_verification_expire",
    }
)

# Models do próprio sistema de auditoria — nunca devem ser auditados (loop).
_NEVER_AUDIT = frozenset({"core.LogModelChange", "core.LogRequest"})

_OLD_INSTANCE_ATTR = "_audit_old_instance"
_IS_NEW_ATTR = "_audit_is_new"


def _enabled() -> bool:
    return bool(getattr(settings, "MODEL_AUDIT_ENABLED", False))


def _audited_labels() -> set[str]:
    raw = getattr(settings, "MODEL_AUDIT_MODELS", "core.User")
    items = [p.strip() for p in raw.split(",") if p.strip()] if isinstance(raw, str) else list(raw)
    return {label for label in items if label not in _NEVER_AUDIT}


def _model_label(sender) -> str:
    return f"{sender._meta.app_label}.{sender.__name__}"


def _serialize(value):
    """Best-effort para JSON. Datas/UUIDs viram str."""
    try:
        import json

        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _instance_to_dict(instance) -> dict:
    out = {}
    for field in instance._meta.concrete_fields:
        name = field.name
        try:
            value = field.value_from_object(instance)
        except Exception:  # noqa: BLE001
            value = None
        if name in _SENSITIVE_FIELDS:
            out[name] = "<redacted>"
        else:
            out[name] = _serialize(value)
    return out


def _diff(old: dict, new: dict) -> dict:
    changed = {}
    keys = set(old) | set(new)
    for k in keys:
        if old.get(k) != new.get(k):
            if k in _SENSITIVE_FIELDS:
                changed[k] = {"old": "<redacted>", "new": "<redacted>"}
            else:
                changed[k] = {"old": old.get(k), "new": new.get(k)}
    return changed


def _actor_kwargs():
    user = get_current_user()
    if user is None:
        return {"actor": None, "actor_email": ""}
    return {"actor": user, "actor_email": getattr(user, "email", "") or ""}


def _on_pre_save(sender, instance, **kwargs):
    if not _enabled() or _model_label(sender) not in _audited_labels():
        return
    if instance.pk is None:
        setattr(instance, _IS_NEW_ATTR, True)
        return
    setattr(instance, _IS_NEW_ATTR, False)
    try:
        old = sender.objects.filter(pk=instance.pk).first()
    except Exception:  # noqa: BLE001
        old = None
    setattr(instance, _OLD_INSTANCE_ATTR, old)


def _on_post_save(sender, instance, created, **kwargs):
    if not _enabled() or _model_label(sender) not in _audited_labels():
        return
    from core.models import LogModelChange

    try:
        if created:
            new_state = _instance_to_dict(instance)
            LogModelChange.objects.create(
                app_label=sender._meta.app_label,
                model_name=sender.__name__,
                object_id=str(instance.pk),
                action=LogModelChange.Action.CREATE,
                changes={"new": new_state},
                **_actor_kwargs(),
            )
            return

        old = getattr(instance, _OLD_INSTANCE_ATTR, None)
        if old is None:
            return  # sem snapshot, não dá para diferenciar; pula
        new_state = _instance_to_dict(instance)
        old_state = _instance_to_dict(old)
        diff = _diff(old_state, new_state)
        if not diff:
            return
        LogModelChange.objects.create(
            app_label=sender._meta.app_label,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            action=LogModelChange.Action.UPDATE,
            changes=diff,
            **_actor_kwargs(),
        )
    except Exception:  # noqa: BLE001 - auditoria nunca pode quebrar a app
        logger.exception("audit post_save falhou para %s", _model_label(sender))


def _on_post_delete(sender, instance, **kwargs):
    if not _enabled() or _model_label(sender) not in _audited_labels():
        return
    from core.models import LogModelChange

    try:
        LogModelChange.objects.create(
            app_label=sender._meta.app_label,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            action=LogModelChange.Action.DELETE,
            changes={"snapshot": _instance_to_dict(instance)},
            **_actor_kwargs(),
        )
    except Exception:  # noqa: BLE001
        logger.exception("audit post_delete falhou para %s", _model_label(sender))


def connect() -> None:
    """Conecta os signals para os models declarados em ``MODEL_AUDIT_MODELS``.

    Chamado de ``CoreConfig.ready`` apenas quando ``MODEL_AUDIT_ENABLED=True``.
    """
    labels = _audited_labels()
    if not labels:
        return
    for label in labels:
        try:
            model = apps.get_model(label)
        except LookupError:
            logger.warning("MODEL_AUDIT_MODELS: %s não encontrado, ignorando.", label)
            continue
        pre_save.connect(_on_pre_save, sender=model, dispatch_uid=f"audit_pre_{label}")
        post_save.connect(_on_post_save, sender=model, dispatch_uid=f"audit_post_{label}")
        post_delete.connect(_on_post_delete, sender=model, dispatch_uid=f"audit_del_{label}")
        logger.info("audit signals conectados para %s", label)
