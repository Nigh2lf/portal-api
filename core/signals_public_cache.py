"""Signals que invalidam o cache público quando um dado exibido no site muda.

A invalidação roda depois do commit e é deduplicada por transação: salvar um imóvel
com 20 fotos gera uma invalidação só. Em importações use
``public_cache.invalidation_batch()`` para juntar tudo em uma no fim.
"""

from __future__ import annotations

import threading

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save

from core.models import (
    Ad,
    AdPlacement,
    Advertiser,
    BlogPost,
    Banner,
    City,
    Feature,
    Neighborhood,
    Plan,
    Portal,
    PortalCity,
    PortalMenuItem,
    Property,
    PropertyFee,
    PropertyPhoto,
    PropertyType,
    State,
    Tip,
)
from core.services import public_cache
from core.services.public_cache import PROPERTY_SCOPES

_pending = threading.local()


def _flush():
    itens = getattr(_pending, "items", None) or {}
    _pending.items = {}
    for (scopes, portal), detalhes in itens.items():
        public_cache.invalidate(list(scopes) if scopes else None, portal, sorted(detalhes) or None)


def _schedule(scopes=None, portal=None, items=()):
    if getattr(public_cache._batch, "active", False):
        public_cache.invalidate_on_commit(scopes, portal, items)
        return
    if not hasattr(_pending, "items"):
        _pending.items = {}
    chave = (tuple(sorted(scopes)) if scopes else None, portal)
    _pending.items.setdefault(chave, set()).update(i for i in items if i)
    transaction.on_commit(_flush)


def _portal_slug(instance):
    pid = getattr(instance, "portal_id", None)
    if not pid:
        return None
    return Portal.objects.filter(pk=pid).values_list("slug", flat=True).first()


def _property_items(prop):
    return [v.lower() for v in (prop.slug, prop.reference_code) if v]


def _on_portal(instance):
    _schedule(None, instance.slug)
    _schedule(["portal"])


def _on_portal_child(instance):
    _schedule(None, _portal_slug(instance))


def _on_menu(instance):
    _schedule(["portal"], _portal_slug(instance))


def _on_content(instance):
    _schedule(["content"], _portal_slug(instance))


def _on_ad_placement(instance):
    _schedule(["content", "plans"])


def _on_plan(instance):
    _schedule(["plans"])


def _on_property(instance):
    _schedule(PROPERTY_SCOPES, None, _property_items(instance))


def _on_property_child(instance):
    prop = Property.objects.filter(pk=instance.property_id).only("slug", "reference_code").first() if instance.property_id else None
    _schedule(PROPERTY_SCOPES, None, _property_items(prop) if prop else ())


def _on_catalog(instance):
    _schedule(PROPERTY_SCOPES)


HANDLERS = {
    Portal: _on_portal,
    PortalCity: _on_portal_child,
    PortalMenuItem: _on_menu,
    Banner: _on_content,
    Ad: _on_content,
    BlogPost: _on_content,
    Tip: _on_content,
    AdPlacement: _on_ad_placement,
    Plan: _on_plan,
    Property: _on_property,
    PropertyPhoto: _on_property_child,
    PropertyFee: _on_property_child,
    Advertiser: _on_catalog,
    PropertyType: _on_catalog,
    City: _on_catalog,
    Neighborhood: _on_catalog,
    Feature: _on_catalog,
    State: _on_catalog,
}


def _post_save(sender, instance, raw=False, **kwargs):
    if not raw:
        HANDLERS[sender](instance)


def _post_delete(sender, instance, **kwargs):
    HANDLERS[sender](instance)


def _property_features_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear") and isinstance(instance, Property):
        _on_property(instance)


def _combined_portals_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear") and isinstance(instance, Portal):
        _on_portal(instance)


def connect():
    for model in HANDLERS:
        post_save.connect(_post_save, sender=model, dispatch_uid=f"public_cache_save_{model.__name__}")
        post_delete.connect(_post_delete, sender=model, dispatch_uid=f"public_cache_delete_{model.__name__}")
    m2m_changed.connect(_property_features_changed, sender=Property.features.through, dispatch_uid="public_cache_property_features")
    m2m_changed.connect(_combined_portals_changed, sender=Portal.combined_portals.through, dispatch_uid="public_cache_combined_portals")
