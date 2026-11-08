"""Capa dos imóveis importados: miniatura e rejeição automática de quem ficou sem foto."""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.models import (
    Advertiser,
    City,
    Plan,
    Portal,
    Property,
    PropertyPhoto,
    PropertyType,
    RejectedProperty,
    State,
    XmlImportError,
    XmlImportRun,
)
from xml_import.formats.base import property_record
from xml_import.services.apply import Applier
from xml_import.services.photos import (
    PHOTO_REJECTION_PREFIX,
    photo_rejection_reason,
    process_cover_photos,
)

OK_URL = "https://fotos.test/ok.jpg"
BROKEN_URL = "https://fotos.test/quebrada.jpg"


def _jpeg() -> bytes:
    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (800, 600), "red").save(out, format="JPEG")
    return out.getvalue()


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def advertiser(db, settings, tmp_path):
    """Anunciante publicado com XML ativo; miniaturas gravadas numa pasta temporária."""
    settings.MEDIA_ROOT = tmp_path
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
    PropertyType.objects.create(name="Casa", slug="casa")
    return Advertiser.objects.create(
        portal=portal,
        plan=plan,
        type=Advertiser.Type.AGENCY,
        name="Ana",
        slug="ana",
        email="ana@x.test",
        is_published=True,
    )


@pytest.fixture
def fake_download(mocker):
    """``download`` devolve um JPEG para ``OK_URL`` e ``None`` (falha) para qualquer outra URL."""
    image = _jpeg()
    return mocker.patch(
        "core.services.images.download",
        side_effect=lambda url, timeout=15: image if url == OK_URL else None,
    )


def _property(advertiser, code, cover_url):
    city = advertiser.portal.main_city
    prop = Property.objects.create(
        advertiser=advertiser,
        reference_code=code,
        slug=f"imovel-{code.lower()}",
        title=f"Imóvel {code}",
        property_type=PropertyType.objects.get(slug="casa"),
        city=city,
        sale_price=100000,
        status=Property.Status.PUBLISHED,
        published_at=timezone.now(),
    )
    PropertyPhoto.objects.create(property=prop, source_url=cover_url, sort_order=1, is_cover=True)
    return prop


def _run(advertiser):
    return XmlImportRun.objects.create(
        advertiser=advertiser, status=XmlImportRun.Status.RUNNING, started_at=timezone.now()
    )


# ------------------------------------------------------------------ miniatura e rejeição


def test_cover_failure_rejects_property(advertiser, fake_download):
    ok = _property(advertiser, "OK1", OK_URL)
    broken = _property(advertiser, "BAD1", BROKEN_URL)
    run = _run(advertiser)

    summary = process_cover_photos(advertiser, run)

    assert summary == {"miniaturas": 1, "rejeitados_sem_foto": ["BAD1"]}
    ok.refresh_from_db()
    broken.refresh_from_db()
    assert ok.photos.get(is_cover=True).thumbnail.name.startswith("properties/thumbs/")
    assert ok.deleted_at is None
    # Imóvel sem capa sai do site, mas a linha fica para a próxima importação revivê-lo.
    assert broken.deleted_at is not None
    assert Property.objects.filter(pk=broken.pk).exists()

    rejected = RejectedProperty.objects.get(advertiser=advertiser, property_reference_code="BAD1")
    assert rejected.reason == photo_rejection_reason(BROKEN_URL)
    assert rejected.reason.startswith(PHOTO_REJECTION_PREFIX)
    error = XmlImportError.objects.get(run=run)
    assert (error.property_reference_code, error.message) == ("BAD1", rejected.reason)


def test_covers_with_thumbnail_are_not_downloaded_again(advertiser, fake_download):
    prop = _property(advertiser, "OK1", OK_URL)
    process_cover_photos(advertiser)
    fake_download.reset_mock()

    summary = process_cover_photos(advertiser)

    assert summary == {"miniaturas": 0, "rejeitados_sem_foto": []}
    fake_download.assert_not_called()
    prop.refresh_from_db()
    assert prop.deleted_at is None


def test_rejection_is_lifted_when_cover_works_again(advertiser, fake_download):
    prop = _property(advertiser, "BAD1", BROKEN_URL)
    process_cover_photos(advertiser)
    assert RejectedProperty.objects.filter(property_reference_code="BAD1").exists()
    # A moderação barrou outro código à mão: isso não é mexido pela importação.
    RejectedProperty.objects.create(
        advertiser=advertiser, property_reference_code="MOD1", reason="Anúncio duplicado"
    )

    # Na importação seguinte o feed traz a capa funcionando e o Applier reviveu o imóvel.
    prop.photos.update(source_url=OK_URL)
    Property.objects.filter(pk=prop.pk).update(deleted_at=None)
    summary = process_cover_photos(advertiser)

    assert summary == {"miniaturas": 1, "rejeitados_sem_foto": []}
    assert not RejectedProperty.objects.filter(property_reference_code="BAD1").exists()
    assert RejectedProperty.objects.filter(property_reference_code="MOD1").exists()


def test_failed_rejection_is_not_duplicated(advertiser, fake_download):
    _property(advertiser, "BAD1", BROKEN_URL)
    process_cover_photos(advertiser)
    Property.objects.filter(reference_code="BAD1").update(deleted_at=None)

    process_cover_photos(advertiser)

    assert RejectedProperty.objects.filter(property_reference_code="BAD1").count() == 1


# ------------------------------------------------------------------ Applier


def test_applier_blocks_only_moderation_rejections(advertiser):
    RejectedProperty.objects.create(
        advertiser=advertiser,
        property_reference_code="FOTO1",
        reason=photo_rejection_reason(BROKEN_URL),
    )
    RejectedProperty.objects.create(
        advertiser=advertiser, property_reference_code="MOD1", reason="Barrado pela moderação"
    )
    feed = [
        property_record(
            codigo=code, cidade="Petrópolis", uf="RJ", tipo="Casa", preco_venda="250000"
        )
        for code in ("FOTO1", "MOD1")
    ]

    result = Applier(advertiser).run(feed, simulate=True)

    assert result.created == ["FOTO1"]
    assert [(i["codigo"], i["motivo"]) for i in result.ignored] == [
        ("MOD1", "Barrado pela moderação.")
    ]


def test_applier_revives_property_rejected_by_photo(advertiser, fake_download):
    prop = _property(advertiser, "BAD1", BROKEN_URL)
    process_cover_photos(advertiser)
    prop.refresh_from_db()
    assert prop.deleted_at is not None

    feed = [
        property_record(
            codigo="BAD1",
            cidade="Petrópolis",
            uf="RJ",
            tipo="Casa",
            preco_venda="100000",
            fotos=[{"url": OK_URL, "capa": True}],
        )
    ]
    Applier(advertiser).run(feed)
    summary = process_cover_photos(advertiser)

    prop.refresh_from_db()
    assert prop.deleted_at is None
    assert summary["rejeitados_sem_foto"] == []
    assert not RejectedProperty.objects.filter(property_reference_code="BAD1").exists()


# ------------------------------------------------------------------ comando generate_cover_thumbnails


def _fake_lock(mocker, acquired=True):
    """Troca a trava do MySQL (GET_LOCK) por uma que devolve ``acquired``."""

    @contextmanager
    def fake(name, wait=0):
        yield acquired

    return mocker.patch("core.management.commands.generate_cover_thumbnails.lock", fake)


def test_command_generates_thumbnails_and_rejects(advertiser, fake_download, mocker):
    _fake_lock(mocker)
    ok = _property(advertiser, "OK1", OK_URL)
    broken = _property(advertiser, "BAD1", BROKEN_URL)

    call_command("generate_cover_thumbnails", "--workers", "2", stdout=StringIO())

    ok.refresh_from_db()
    broken.refresh_from_db()
    assert ok.photos.get(is_cover=True).thumbnail.name
    assert ok.deleted_at is None
    assert broken.deleted_at is not None
    assert RejectedProperty.objects.get(property_reference_code="BAD1").reason.startswith(
        PHOTO_REJECTION_PREFIX
    )


def test_command_no_reject_only_generates(advertiser, fake_download, mocker):
    _fake_lock(mocker)
    broken = _property(advertiser, "BAD1", BROKEN_URL)

    call_command("generate_cover_thumbnails", "--no-reject", stdout=StringIO())

    broken.refresh_from_db()
    assert broken.deleted_at is None
    assert not RejectedProperty.objects.exists()


def test_command_skips_advertiser_being_imported(advertiser, fake_download, mocker):
    _fake_lock(mocker, acquired=False)
    broken = _property(advertiser, "BAD1", BROKEN_URL)
    out = StringIO()

    call_command("generate_cover_thumbnails", stdout=out)

    broken.refresh_from_db()
    assert broken.deleted_at is None
    fake_download.assert_not_called()
    assert "1 anunciantes pulados" in out.getvalue()
