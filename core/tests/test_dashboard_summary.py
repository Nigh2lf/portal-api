"""Contadores do painel inicial do admin (``/summary/`` de usuários, anunciantes e imóveis)."""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
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
    Property,
    PropertyType,
    State,
    User,
    UserProfile,
)


def _grant(user, *views):
    profile = Profile.objects.create(name="Painel")
    for view in views:
        menu = Menu.objects.create(name=view, view=view)
        perm = Permission.objects.create(menu=menu, name=f"{view} READ", type="READ")
        ProfilePermission.objects.create(profile=profile, permission=perm)
    UserProfile.objects.create(user=user, profile=profile)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def scenario(db):
    state = State.objects.create(name="Rio de Janeiro", code="RJ")
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
    kind = PropertyType.objects.create(name="Casa", slug="casa")

    def advertiser(name, published, xml=False, logged=False):
        user = User.objects.create_user(email=f"{name}@x.test", password="Strong#Pass1234")
        if logged:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
        adv = Advertiser.objects.create(
            portal=portal, plan=plan, type=Advertiser.Type.AGENCY, name=name, slug=name,
            email=f"{name}@x.test", is_published=published, user=user,
        )
        AdvertiserIntegration.objects.create(
            advertiser=adv, xml_url="https://x.test/f.xml" if xml else "", is_active=xml
        )
        return adv

    def prop(adv, code, active=True, **extra):
        return Property.objects.create(
            advertiser=adv, reference_code=code, slug=f"{adv.slug}-{code}", title=code,
            property_type=kind, city=city, status=Property.Status.PUBLISHED, is_active=active, **extra,
        )

    on = advertiser("on", True, xml=True, logged=True)
    empty = advertiser("empty", True)
    off = advertiser("off", False, xml=True)
    prop(on, "1")
    prop(on, "2", imported_at=timezone.now())
    prop(on, "3", active=False)
    prop(off, "4")
    prop(on, "5", deleted_at=timezone.now())
    blocked = User.objects.create_user(email="blocked@x.test", password="Strong#Pass1234")
    blocked.is_active = False
    blocked.save(update_fields=["is_active"])
    return {"on": on, "empty": empty, "off": off}


def test_summaries_count_total_and_active(scenario, admin_user):
    client = _grant(admin_user, "user", "advertiser", "property")

    users = client.get("/api/v1/users/summary/").json()["data"]
    assert users == {"total": 5, "active": 4, "logged_in": 1, "of_published_advertisers": 2, "admins": 1}

    advertisers = client.get("/api/v1/advertisers/summary/").json()["data"]
    assert advertisers == {"total": 3, "published": 2, "published_with_properties": 1, "with_active_xml": 2}

    properties = client.get("/api/v1/properties/summary/").json()["data"]
    assert properties == {"total": 4, "visible": 2, "hidden_by_advertiser": 1, "inactive": 1, "of_xml_advertisers": 4}


def test_summary_is_one_aggregate_query(scenario):
    from core.modules.advertiser.service import AdvertiserService
    from core.modules.property.service import PropertyService
    from core.modules.user.service import UserService

    for service in (UserService, AdvertiserService, PropertyService):
        with CaptureQueriesContext(connection) as queries:
            service.summary()
        assert len(queries) == 1


def test_summary_requires_read_permission_of_its_own_screen(scenario, admin_user):
    client = _grant(admin_user, "user")
    assert client.get("/api/v1/users/summary/").status_code == 200
    assert client.get("/api/v1/properties/summary/").status_code == 403
    assert APIClient().get("/api/v1/advertisers/summary/").status_code in (401, 403)
