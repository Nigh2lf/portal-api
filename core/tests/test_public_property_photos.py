"""Fotos sob demanda do card da listagem: ``GET /public/portals/<portal>/properties/<imóvel>/photos/``."""

from __future__ import annotations

import pytest
from django.utils import timezone

from core.models import (
    Advertiser,
    City,
    Plan,
    Portal,
    PortalCity,
    Property,
    PropertyPhoto,
    PropertyType,
    State,
)


@pytest.fixture
def visible_property(db):
    """Imóvel publicado de Petrópolis com três fotos externas; a capa é a de ordem 2."""
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
    PortalCity.objects.create(portal=portal, city=city)
    plan = Plan.objects.create(name="Básico", slug="basico", property_limit=100, photo_limit=10)
    advertiser = Advertiser.objects.create(
        portal=portal,
        plan=plan,
        type=Advertiser.Type.AGENCY,
        name="Ana",
        slug="ana",
        email="ana@x.test",
        is_published=True,
    )
    prop = Property.objects.create(
        advertiser=advertiser,
        reference_code="ABC1",
        slug="casa-abc1",
        title="Casa",
        property_type=PropertyType.objects.create(name="Casa", slug="casa"),
        city=city,
        sale_price=100000,
        status=Property.Status.PUBLISHED,
        published_at=timezone.now(),
    )
    for order, is_cover in ((1, False), (2, True), (3, False)):
        PropertyPhoto.objects.create(
            property=prop,
            source_url=f"http://fotos.test/{order}.jpg",
            sort_order=order,
            is_cover=is_cover,
        )
    return prop


URL = "/api/v1/public/portals/petropolis/properties/{}/photos/"


def test_photos_come_cover_first(api_client, visible_property):
    r = api_client.get(URL.format(visible_property.slug))

    assert r.status_code == 200, r.content
    photos = r.json()["data"]
    assert [p["url"] for p in photos] == [
        "http://fotos.test/2.jpg",
        "http://fotos.test/1.jpg",
        "http://fotos.test/3.jpg",
    ]
    assert photos[0]["is_cover"] is True


def test_photos_by_reference_code(api_client, visible_property):
    r = api_client.get(URL.format("abc1"))

    assert r.status_code == 200 and len(r.json()["data"]) == 3


def test_photos_404_when_property_is_not_visible(api_client, visible_property):
    visible_property.delete()

    assert api_client.get(URL.format(visible_property.slug)).status_code == 404
