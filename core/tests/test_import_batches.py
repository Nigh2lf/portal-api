"""Lotes da importação XML: queue, progresso, cancelamento cooperativo e endpoints do painel."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    Advertiser,
    AdvertiserIntegration,
    City,
    Menu,
    Permission,
    Plan,
    Portal,
    Profile,
    ProfilePermission,
    State,
    UserProfile,
    XmlImportBatch,
    XmlImportRun,
)
from xml_import.services import batches
from xml_import.services.apply import Applier
from xml_import.services.cancellation import ImportCancelled
from xml_import.services.download import ImportFailed

Status = XmlImportBatch.Status
RunStatus = XmlImportRun.Status


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def advertisers(db):
    """Três advertisers publicados com XML active: Ana, Bia e Caio."""
    state = State.objects.create(code="RJ", name="Rio de Janeiro")
    city = City.objects.create(state=state, name="Petrópolis", slug="petropolis")
    portal = Portal.objects.create(
        slug="petropolis",
        name="Petrópolis Imóveis",
        domain="petropolis.test",
        main_city=city,
        email="contato@petropolis.test",
        seo_title="t",
        seo_description="d",
    )
    plan = Plan.objects.create(name="Básico", slug="basico", property_limit=100, photo_limit=10)
    out = []
    for nome in ("Ana", "Bia", "Caio"):
        advertiser = Advertiser.objects.create(
            portal=portal,
            plan=plan,
            type=Advertiser.Type.AGENCY,
            name=nome,
            slug=nome.lower(),
            email=f"{nome.lower()}@x.test",
            is_published=True,
        )
        AdvertiserIntegration.objects.create(
            advertiser=advertiser, xml_url=f"https://x.test/{nome.lower()}.xml", is_active=True
        )
        out.append(advertiser)
    return out


@pytest.fixture
def admin_api(admin_user):
    """Cliente autenticado como admin com CREATE e READ em ``xml_import_run``."""
    menu = Menu.objects.create(name="Importações XML", view="xml_import_run")
    profile = Profile.objects.create(name="Admin")
    for kind in ("READ", "CREATE"):
        perm = Permission.objects.create(menu=menu, name=f"xml_import_run {kind}", type=kind)
        ProfilePermission.objects.create(profile=profile, permission=perm)
    UserProfile.objects.create(user=admin_user, profile=profile)
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


def _run_ok(batch, advertiser):
    now = timezone.now()
    XmlImportRun.objects.create(
        advertiser=advertiser,
        batch=batch,
        status=RunStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        total_properties=5,
        valid_properties=5,
    )


def _fake_importer(mocker, effect):
    """Substitui ``import_advertiser`` no lote por ``effect(advertiser, batch, cancel_check)``."""

    def fake(
        advertiser,
        simulate=False,
        download=True,
        origin_label="manual",
        batch=None,
        cancel_check=None,
    ):
        return effect(advertiser, batch, cancel_check)

    return mocker.patch("xml_import.services.batches.import_advertiser", side_effect=fake)


# ------------------------------------------------------------------ queue


def test_create_batch_all_orders_by_last_import(advertisers):
    ana, bia, caio = advertisers
    bia.integration.last_imported_at = timezone.now() - timedelta(days=1)
    bia.integration.save()
    caio.integration.last_imported_at = timezone.now() - timedelta(days=5)
    caio.integration.save()

    batch = batches.create_batch()

    assert batch.scope == XmlImportBatch.Scope.ALL
    assert batch.status == Status.QUEUED
    assert batch.total_advertisers == 3
    # Quem nunca importou vai primeiro; depois quem está há mais tempo sem importar.
    assert batch.advertiser_ids == [str(ana.pk), str(caio.pk), str(bia.pk)]


def test_advertiser_queue_ignores_without_xml(advertisers):
    ana, bia, _ = advertisers
    bia.integration.is_active = False
    bia.integration.save()
    ghost = uuid.uuid4()

    queue, invalid = batches.advertiser_queue([ana.pk, bia.pk, ghost])

    assert [a.pk for a in queue] == [ana.pk]
    assert invalid == [str(bia.pk), str(ghost)]


def test_create_batch_without_advertisers(db):
    with pytest.raises(batches.EmptyBatch):
        batches.create_batch()


# ------------------------------------------------------------------ execução


def test_run_batch_success(advertisers, mocker):
    _fake_importer(mocker, lambda advertiser, batch, _c: _run_ok(batch, advertiser))
    batch = batches.create_batch()

    summary = batches.run_batch(batch.pk, lock_wait=0)

    batch.refresh_from_db()
    assert summary["importados"] == 3
    assert batch.status == Status.SUCCESS
    assert (batch.done, batch.ok, batch.failed, batch.cancelled) == (3, 3, 0, 0)
    assert batch.finished_at is not None and batch.current_advertiser is None
    assert batch.runs.count() == 3


def test_run_batch_with_failure_is_partial(advertisers, mocker):
    def effect(advertiser, batch, _c):
        if advertiser.name == "Bia":
            raise ImportFailed("Feed sem imóveis: nada foi alterado.")
        _run_ok(batch, advertiser)

    _fake_importer(mocker, effect)
    batch = batches.create_batch()

    batches.run_batch(batch.pk, lock_wait=0)

    batch.refresh_from_db()
    assert batch.status == Status.PARTIAL
    assert (batch.ok, batch.failed) == (2, 1)
    assert "Bia: Feed sem imóveis" in batch.error_message


def test_run_batch_all_failures(advertisers, mocker):
    def effect(advertiser, batch, _c):
        raise ImportFailed("fora do ar")

    _fake_importer(mocker, effect)
    batch = batches.create_batch()
    batches.run_batch(batch.pk, lock_wait=0)
    batch.refresh_from_db()
    assert batch.status == Status.FAILED


def test_cron_skips_imported_today_and_respects_window(advertisers, mocker):
    ana, bia, caio = advertisers
    ana.integration.last_imported_at = timezone.now()
    ana.integration.save()
    _fake_importer(mocker, lambda advertiser, batch, _c: _run_ok(batch, advertiser))
    # Janela já encerrada: ninguém novo começa.
    batch = batches.create_batch(
        origin=XmlImportBatch.Origin.CRON, deadline_at=timezone.now() - timedelta(minutes=1)
    )

    summary = batches.run_batch(batch.pk, lock_wait=0)

    batch.refresh_from_db()
    assert summary == {
        "importados": 0,
        "falhas": 0,
        "ja_importados_hoje": 1,
        "para_proxima_noite": 2,
        "cancelados": 0,
    }
    assert batch.status == Status.SUCCESS
    assert batch.skipped == 3
    assert set(batch.runs.values_list("status", flat=True)) == {RunStatus.SKIPPED}


# ------------------------------------------------------------------ cancelamento


def test_cancel_queued_batch(advertisers):
    batch = batches.create_batch()

    batch = batches.cancel_batch(batch)

    assert batch.status == Status.CANCELLED
    assert (batch.done, batch.cancelled) == (3, 3)
    assert batch.runs.filter(status=RunStatus.CANCELLED).count() == 3
    with pytest.raises(batches.BatchNotCancellable):
        batches.cancel_batch(batch)


def test_cancel_between_advertisers(advertisers, mocker):
    """O admin cancela enquanto o primeiro anunciante roda: ele termina, os outros não começam."""

    def effect(advertiser, batch, _c):
        _run_ok(batch, advertiser)
        batches.cancel_batch(XmlImportBatch.objects.get(pk=batch.pk))

    _fake_importer(mocker, effect)
    batch = batches.create_batch()

    summary = batches.run_batch(batch.pk, lock_wait=0)

    batch.refresh_from_db()
    assert batch.status == Status.CANCELLED
    assert (batch.done, batch.ok, batch.cancelled) == (3, 1, 2)
    assert summary["cancelados"] == 2
    assert batch.runs.filter(status=RunStatus.SUCCESS).count() == 1
    assert batch.runs.filter(status=RunStatus.CANCELLED).count() == 2


def test_cancel_inside_advertiser(advertisers, mocker):
    """O ponto de checagem dentro do anunciante levanta ``ImportCancelled``; o lote fecha sem gravar os demais."""

    def effect(advertiser, batch, cancel_check):
        batches.cancel_batch(XmlImportBatch.objects.get(pk=batch.pk))
        assert cancel_check() is True
        now = timezone.now()
        XmlImportRun.objects.create(
            advertiser=advertiser,
            batch=batch,
            status=RunStatus.CANCELLED,
            started_at=now,
            finished_at=now,
        )
        raise ImportCancelled("cancel_check")

    _fake_importer(mocker, effect)
    batch = batches.create_batch()

    batches.run_batch(batch.pk, lock_wait=0)

    batch.refresh_from_db()
    assert batch.status == Status.CANCELLED
    assert (batch.done, batch.ok, batch.cancelled) == (3, 0, 3)
    assert batch.heartbeat_at is not None


def test_cancel_check_renews_heartbeat(advertisers):
    batch = batches.create_batch()
    XmlImportBatch.objects.filter(pk=batch.pk).update(
        status=Status.RUNNING, heartbeat_at=timezone.now() - timedelta(hours=1)
    )
    cancel_check = batches._cancel_check(batch.pk)

    assert cancel_check() is False
    batch.refresh_from_db()
    assert batch.heartbeat_at > timezone.now() - timedelta(minutes=1)


def test_applier_stops_at_first_checkpoint(advertisers):
    with pytest.raises(ImportCancelled):
        Applier(advertisers[0]).run([{"codigo": "A1"}], cancel_check=lambda: True)


def test_abandoned_batch_fails(advertisers):
    batch = batches.create_batch()
    now = timezone.now()
    XmlImportRun.objects.create(
        advertiser=advertisers[0], batch=batch, status=RunStatus.RUNNING, started_at=now
    )
    XmlImportBatch.objects.filter(pk=batch.pk).update(
        status=Status.RUNNING, heartbeat_at=now - timedelta(hours=1)
    )

    assert batches.active_batch() is None

    batch.refresh_from_db()
    assert batch.status == Status.FAILED
    assert "sem batimento" in batch.error_message
    assert batch.runs.get(advertiser=advertisers[0]).status == RunStatus.FAILED
    assert batch.runs.filter(status=RunStatus.SKIPPED).count() == 2


def test_active_batch_keeps_heartbeating_one(advertisers):
    batch = batches.create_batch()
    XmlImportBatch.objects.filter(pk=batch.pk).update(
        status=Status.RUNNING, heartbeat_at=timezone.now()
    )
    assert batches.active_batch().pk == batch.pk


# ------------------------------------------------------------------ endpoints


BASE = "/api/v1/xml-import-runs/batches/"


def test_api_creates_batch_for_all(advertisers, admin_api, mocker):
    thread = mocker.patch("core.modules.xml_import_run.view.start_batch_in_background")

    r = admin_api.post(BASE, {}, format="json")

    assert r.status_code == 202, r.content
    data = r.json()["data"]
    assert data["scope"] == "ALL" and data["total_advertisers"] == 3 and data["status"] == "QUEUED"
    assert [p["name"] for p in data["pending"]] == ["Ana", "Bia", "Caio"]
    thread.assert_called_once()
    assert (
        XmlImportBatch.objects.get(pk=data["id"]).created_by_id == admin_api.handler._force_user.pk
    )


def test_api_creates_selected_batch(advertisers, admin_api, mocker):
    mocker.patch("core.modules.xml_import_run.view.start_batch_in_background")
    ana, _, caio = advertisers

    r = admin_api.post(BASE, {"advertisers": [str(caio.pk), str(ana.pk)]}, format="json")

    assert r.status_code == 202, r.content
    data = r.json()["data"]
    assert data["scope"] == "SELECTED"
    assert [p["name"] for p in data["pending"]] == ["Ana", "Caio"]


def test_api_rejects_without_xml_and_empty_list(advertisers, admin_api):
    assert (
        admin_api.post(BASE, {"advertisers": [str(uuid.uuid4())]}, format="json").status_code == 400
    )
    assert admin_api.post(BASE, {"advertisers": []}, format="json").status_code == 400


def test_api_409_when_advertiser_in_active_batch(advertisers, admin_api, mocker):
    mocker.patch("core.modules.xml_import_run.view.start_batch_in_background")
    ana = advertisers[0]
    assert admin_api.post(BASE, {"advertisers": [str(ana.pk)]}, format="json").status_code == 202

    r = admin_api.post(BASE, {}, format="json")

    assert r.status_code == 409
    assert "lote em andamento" in r.json()["message"]


def test_api_active_batch_and_cancel(advertisers, admin_api, mocker):
    mocker.patch("core.modules.xml_import_run.view.start_batch_in_background")
    created = admin_api.post(BASE, {}, format="json").json()["data"]

    active = admin_api.get(f"{BASE}active/")
    assert active.status_code == 200 and active.json()["data"]["id"] == created["id"]

    cancel = admin_api.post(f"{BASE}{created['id']}/cancel/")
    assert cancel.status_code == 200, cancel.content
    assert cancel.json()["data"]["status"] == "CANCELLED"
    assert cancel.json()["data"]["cancelled"] == 3

    assert admin_api.post(f"{BASE}{created['id']}/cancel/").status_code == 409
    assert admin_api.get(f"{BASE}active/").json()["data"] is None
    detail = admin_api.get(f"{BASE}{created['id']}/").json()["data"]
    assert len(detail["runs"]) == 3 and detail["pending"] == []
    assert admin_api.get(BASE).json()["data"][0]["id"] == created["id"]


def test_api_run_imports_as_single_batch(advertisers, admin_api, mocker):
    thread = mocker.patch("core.modules.xml_import_run.view.start_batch_in_background")
    ana = advertisers[0]

    r = admin_api.post(
        "/api/v1/xml-import-runs/run/",
        {"advertiser": str(ana.pk), "simulate": False},
        format="json",
    )

    assert r.status_code == 202, r.content
    batch = XmlImportBatch.objects.get(pk=r.json()["data"]["batch"])
    assert batch.scope == "SELECTED" and batch.advertiser_ids == [str(ana.pk)]
    thread.assert_called_once_with(batch.pk)


def test_api_runs_list_filters_by_batch(advertisers, admin_api):
    batch = batches.create_batch()
    _run_ok(batch, advertisers[0])
    _run_ok(None, advertisers[1])

    r = admin_api.get(f"/api/v1/xml-import-runs/?batch={batch.pk}")

    assert r.status_code == 200
    results = r.json()["data"]["results"]
    assert len(results) == 1 and results[0]["status"] == "SUCCESS"


def test_api_requires_permission(advertisers, user):
    client = APIClient()
    client.force_authenticate(user)
    assert client.post(BASE, {}, format="json").status_code == 403
