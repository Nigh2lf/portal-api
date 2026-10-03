"""Auto-registro inteligente de modelos no Django Admin.

Para cada modelo de um app:
- Se já houver um ``ModelAdmin`` registrado manualmente, **não toca**.
- Caso contrário, registra um ``ModelAdmin`` com ``list_display``,
  ``search_fields``, ``list_filter``, ``readonly_fields``, ``ordering`` e
  ``date_hierarchy`` inferidos automaticamente da definição do modelo.

Uso (em ``core/admin.py``):

    from core.classes.auto_admin import autoregister
    autoregister("core")
"""

from __future__ import annotations

from django.apps import apps
from django.contrib import admin
from django.db import models

# Campos que nunca aparecem em list_display (pesados ou sensíveis).
_HEAVY_FIELDS = (models.TextField, models.JSONField, models.BinaryField)
_SENSITIVE_NAMES = frozenset(
    {
        "password",
        "forgot_password_hash",
        "forgot_password_expire",
        "email_verification_code",
        "email_verification_expire",
    }
)
_AUDIT_NAMES = frozenset({"id", "created_at", "updated_at", "deleted_at", "deleted_by"})
# Limite de FKs em list_filter — muitas FKs deixam o admin lento.
_MAX_FK_FILTERS = 3


def _infer_list_display(model) -> tuple[str, ...]:
    out: list[str] = []
    for f in model._meta.fields:
        if f.name in _SENSITIVE_NAMES:
            continue
        if isinstance(f, _HEAVY_FIELDS):
            continue
        out.append(f.name)
    # PK primeiro, depois str-like, depois booleans/datetimes.
    return tuple(out[:8])  # cap em 8 colunas para não estourar a tela


def _infer_search_fields(model) -> tuple[str, ...]:
    out: list[str] = []
    for f in model._meta.fields:
        if f.name in _SENSITIVE_NAMES:
            continue
        if isinstance(f, models.CharField | models.EmailField | models.SlugField | models.URLField):
            out.append(f.name)
        elif isinstance(f, models.ForeignKey):
            related = f.related_model
            for candidate in ("name", "email", "title", "slug"):
                if candidate in [rf.name for rf in related._meta.fields]:
                    out.append(f"{f.name}__{candidate}")
                    break
    return tuple(out)


def _infer_list_filter(model) -> tuple[str, ...]:
    out: list[str] = []
    fk_count = 0
    for f in model._meta.fields:
        if f.name in _SENSITIVE_NAMES:
            continue
        if (
            isinstance(f, models.BooleanField)
            or getattr(f, "choices", None)
            or isinstance(f, models.DateTimeField)
            and f.name in {"created_at", "updated_at", "deleted_at"}
        ):
            out.append(f.name)
        elif isinstance(f, models.ForeignKey) and fk_count < _MAX_FK_FILTERS:
            out.append(f.name)
            fk_count += 1
    return tuple(out)


def _infer_readonly_fields(model) -> tuple[str, ...]:
    field_names = {f.name for f in model._meta.fields}
    return tuple(n for n in _AUDIT_NAMES if n in field_names)


def _infer_date_hierarchy(model) -> str | None:
    for candidate in ("created_at", "updated_at"):
        if candidate in [f.name for f in model._meta.fields]:
            return candidate
    return None


def _infer_ordering(model) -> tuple[str, ...]:
    field_names = {f.name for f in model._meta.fields}
    if "created_at" in field_names:
        return ("-created_at",)
    return ()


def _build_admin_class(model) -> type[admin.ModelAdmin]:
    attrs = {
        "list_display": _infer_list_display(model),
        "search_fields": _infer_search_fields(model),
        "list_filter": _infer_list_filter(model),
        "readonly_fields": _infer_readonly_fields(model),
        "ordering": _infer_ordering(model),
        "list_per_page": 25,
        "save_on_top": True,
    }
    date_hier = _infer_date_hierarchy(model)
    if date_hier:
        attrs["date_hierarchy"] = date_hier

    return type(f"Auto{model.__name__}Admin", (admin.ModelAdmin,), attrs)


def autoregister(app_label: str) -> list[type]:
    """Registra todos os modelos do ``app_label`` que ainda não têm admin.

    Retorna a lista de modelos efetivamente registrados.
    """
    registered = []
    for model in apps.get_app_config(app_label).get_models():
        if admin.site.is_registered(model):
            continue
        admin.site.register(model, _build_admin_class(model))
        registered.append(model)
    return registered
