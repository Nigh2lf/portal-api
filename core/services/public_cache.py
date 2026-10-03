"""Cache das respostas públicas do site (app ``public``) com invalidação por versão.

- Dados: cache ``default`` (memória do processo).
- Versões: cache ``cache_versions`` (arquivo local), compartilhado pelos workers do
  mesmo container. Invalidar = gravar uma versão nova; as chaves antigas deixam de
  ser lidas e expiram sozinhas, sem varredura.
- Site: cada invalidação avisa o portal-web (``SITE_REVALIDATE_URL``), que expira as
  tags equivalentes do cache do Next.

Trocar para Redis no futuro é só apontar os dois aliases de ``CACHES`` para ele.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

SCOPES = {
    "portal": "Configuração do portal e menus",
    "home": "Blocos da home (destaques, mais procurados, bairros)",
    "listing": "Busca e detalhe de imóveis",
    "catalog": "Opções da busca (tipos, cidades, bairros, características)",
    "content": "Banners, anúncios, blog e dicas",
    "advertiser": "Imobiliárias e hotsites",
    "plans": "Planos e tabela de publicidade",
}

TIMEOUTS = {
    "portal": 3600,
    "home": 900,
    "listing": 300,
    "catalog": 1800,
    "content": 3600,
    "advertiser": 900,
    "plans": 3600,
}

# Imóvel ou anunciante alterado mexe em tudo que conta ou lista imóveis.
PROPERTY_SCOPES = ("listing", "home", "catalog", "advertiser", "portal")

HISTORY_KEY = "history"
HISTORY_SIZE = 50
_MISS = object()
_batch = threading.local()
_request_hits: contextvars.ContextVar[list[bool] | None] = contextvars.ContextVar("public_cache_hits", default=None)


def start_tracking():
    """Começa a anotar acertos/falhas do cache na request atual (usado pelo log de requests)."""
    return _request_hits.set([])


def stop_tracking(token):
    """
    Encerra a anotação e resume o resultado

    Args:
        token: retorno de ``start_tracking``

    Returns:
        ``"HIT"`` se todas as consultas acertaram, ``"MISS"`` se alguma foi ao banco, ``""`` se não houve consulta
    """
    hits = _request_hits.get() or []
    _request_hits.reset(token)
    if not hits:
        return ""
    return "HIT" if all(hits) else "MISS"


def _track(hit):
    hits = _request_hits.get()
    if hits is not None:
        hits.append(hit)


def is_enabled():
    return getattr(settings, "PUBLIC_CACHE_ENABLED", True)


def _data():
    return caches["default"]


def _versions():
    return caches["cache_versions"]


def _version_keys(scope, portal=None, item=None):
    keys = ["all", f"s:{scope}"]
    if portal:
        keys += [f"p:{portal}", f"ps:{portal}:{scope}"]
    if item:
        keys.append(f"i:{scope}:{item}")
    return keys


def cached(scope, builder, *, portal=None, params=None, item=None, timeout=None):
    """
    Devolve o valor em cache ou executa ``builder`` e guarda o resultado

    Args:
        scope: um dos ``SCOPES``; define a validade e quem invalida
        builder: função sem argumentos que monta o valor (exceções não são guardadas)
        portal: slug do portal, quando o dado é de um portal
        params: dict com o que diferencia a resposta (filtros, página, limite)
        item: identificador fino (ex.: slug do imóvel) para invalidação individual
        timeout: segundos; padrão em ``TIMEOUTS``

    Returns:
        o valor (cópia, o cache em memória serializa com pickle)
    """
    if not is_enabled():
        return builder()
    vkeys = _version_keys(scope, portal, item)
    try:
        versions = _versions().get_many(vkeys)
    except Exception:  # noqa: BLE001 - cache de versões indisponível não pode derrubar o site
        logger.exception("public_cache: falha ao ler versões")
        return builder()
    stamp = ".".join(str(versions.get(k, 0)) for k in vkeys)
    raw = json.dumps(params or {}, sort_keys=True, default=str)
    digest = hashlib.sha1(f"{scope}|{portal}|{item}|{raw}|{stamp}".encode()).hexdigest()
    key = f"pub:{scope}:{portal or '-'}:{digest}"
    hit = _data().get(key, _MISS)
    _track(hit is not _MISS)
    if hit is not _MISS:
        return hit
    value = builder()
    _data().set(key, value, timeout or TIMEOUTS.get(scope, 600))
    return value


def site_tags(scopes=None, portal=None):
    """
    Tags do cache do Next equivalentes a uma invalidação

    Args:
        scopes: lista de escopos ou ``None`` (todos)
        portal: slug ou ``None`` (todos os portais)

    Returns:
        lista de tags
    """
    if not scopes and not portal:
        return ["pub"]
    if not portal:
        return [f"pub:{s}" for s in scopes]
    tags = [f"portal:{portal}"] if not scopes else [f"portal:{portal}:{s}" for s in scopes]
    # O site resolve o portal pelo host antes de saber o slug; essa busca tem tag própria.
    if not scopes or "portal" in scopes:
        tags.append("pub:hosts")
    return tags


def _bump(scopes=None, portal=None, items=None):
    agora = time.time_ns()
    keys = [f"i:listing:{i}" for i in items or ()]
    if not scopes and not portal:
        if not keys:
            keys.append("all")
    elif not portal:
        keys += [f"s:{s}" for s in scopes]
    elif not scopes:
        keys.append(f"p:{portal}")
    else:
        keys += [f"ps:{portal}:{s}" for s in scopes]
    _versions().set_many({k: agora for k in keys}, None)


def notify_site(tags):
    """
    Pede ao portal-web para expirar as tags informadas

    Args:
        tags: lista de tags do cache do Next

    Returns:
        ``{"ok": bool, "status": int|None, "error": str}``
    """
    url = getattr(settings, "SITE_REVALIDATE_URL", "")
    if not url:
        return {"ok": False, "status": None, "error": "SITE_REVALIDATE_URL não configurada."}
    body = json.dumps({"tags": tags}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "x-revalidate-secret": getattr(settings, "SITE_REVALIDATE_SECRET", "")},
    )
    try:
        with urllib.request.urlopen(req, timeout=getattr(settings, "SITE_REVALIDATE_TIMEOUT", 5)) as res:
            return {"ok": 200 <= res.status < 300, "status": res.status, "error": ""}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": f"HTTP {exc.code}"}
    except Exception as exc:  # noqa: BLE001 - site fora do ar não pode quebrar quem invalidou
        return {"ok": False, "status": None, "error": str(exc)[:200]}


def _notify_async(tags):
    def run():
        r = notify_site(tags)
        if not r["ok"] and getattr(settings, "SITE_REVALIDATE_URL", ""):
            logger.warning("public_cache: site não revalidou %s: %s", tags, r["error"])

    threading.Thread(target=run, daemon=True).start()


def _record(entry):
    try:
        historico = _versions().get(HISTORY_KEY) or []
        _versions().set(HISTORY_KEY, [entry, *historico][:HISTORY_SIZE], None)
    except Exception:  # noqa: BLE001
        logger.exception("public_cache: falha ao gravar histórico")


def history():
    return _versions().get(HISTORY_KEY) or []


def invalidate(scopes=None, portal=None, items=None, *, origin="auto", user=None, wait_site=False):
    """
    Invalida o cache público da API e avisa o site

    Args:
        scopes: escopos afetados; ``None`` = todos
        portal: slug do portal; ``None`` = todos
        items: identificadores de imóvel (slug/código, minúsculos) para o detalhe
        origin: ``auto`` (sinais), ``manual`` (admin) ou ``batch`` (importações)
        user: e-mail de quem pediu, para o histórico
        wait_site: ``True`` espera a resposta do site (uso no admin)

    Returns:
        ``{"tags": [...], "site": {...}|None}``
    """
    scopes = [s for s in (scopes or []) if s in SCOPES] or None
    if getattr(_batch, "active", False):
        _batch.scopes.update(scopes or SCOPES)
        return {"tags": [], "site": None}
    _bump(scopes, portal, items)
    # Detalhe de imóvel não fica no cache do Next; limpar só um imóvel não precisa avisar o site.
    tags = [] if items and not scopes and not portal else site_tags(scopes, portal)
    site = None
    if tags and wait_site:
        site = notify_site(tags)
    elif tags:
        _notify_async(tags)
    if origin != "auto":
        _record(
            {
                "at": timezone.now().isoformat(),
                "origin": origin,
                "user": user or "",
                "portal": portal or "",
                "scopes": scopes or [],
                "items": list(items or []),
                "site_ok": site["ok"] if site else None,
                "site_error": site["error"] if site else "",
            }
        )
    return {"tags": tags, "site": site}


def invalidate_on_commit(scopes=None, portal=None, items=None):
    """Agenda a invalidação para depois do commit da transação atual."""
    if getattr(_batch, "active", False):
        _batch.scopes.update(scopes or SCOPES)
        return
    transaction.on_commit(lambda: invalidate(scopes, portal, items))


@contextmanager
def invalidation_batch(user=None):
    """
    Junta as invalidações de um processamento em lote (importação) em uma só no fim

    Args:
        user: identificação para o histórico
    """
    if getattr(_batch, "active", False):
        yield
        return
    _batch.active = True
    _batch.scopes = set()
    try:
        yield
    finally:
        scopes = sorted(_batch.scopes)
        _batch.active = False
        _batch.scopes = set()
        if scopes:
            invalidate(scopes, origin="batch", user=user)
