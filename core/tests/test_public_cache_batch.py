"""Lote de invalidação do cache público (``public_cache.invalidation_batch``)."""

from __future__ import annotations

from core.services import public_cache


def test_batch_invalidates_only_touched_scopes(mocker):
    invalidate = mocker.patch.object(public_cache, "invalidate", return_value={"tags": ["t"], "site": None})
    with public_cache.invalidation_batch(user="x") as result:
        public_cache._batch.scopes.add("listing")
    invalidate.assert_called_once_with(["listing"], origin="batch", user="x", wait_site=False)
    assert result == {"tags": ["t"], "site": None}


def test_batch_without_changes_does_nothing(mocker):
    invalidate = mocker.patch.object(public_cache, "invalidate")
    with public_cache.invalidation_batch(user="x") as result:
        pass
    invalidate.assert_not_called()
    assert result == {}


def test_batch_everything_clears_all_and_waits_site(mocker):
    site = {"ok": False, "status": None, "error": "SITE_REVALIDATE_URL não configurada."}
    invalidate = mocker.patch.object(public_cache, "invalidate", return_value={"tags": ["a"], "site": site})
    with public_cache.invalidation_batch(user="import_legacy", everything=True, wait_site=True) as result:
        pass  # nenhum sinal disparado (gravações em lote), mesmo assim limpa tudo
    invalidate.assert_called_once_with(None, origin="batch", user="import_legacy", wait_site=True)
    assert result["site"] == site
    assert not public_cache._batch.active


def test_nested_batch_defers_to_outer(mocker):
    invalidate = mocker.patch.object(public_cache, "invalidate", return_value={"tags": [], "site": None})
    with public_cache.invalidation_batch(user="outer", everything=True):
        with public_cache.invalidation_batch(user="inner") as inner:
            public_cache._batch.scopes.add("home")
        assert inner == {}
        invalidate.assert_not_called()
    invalidate.assert_called_once_with(None, origin="batch", user="outer", wait_site=False)
