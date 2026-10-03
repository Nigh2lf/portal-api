"""Rotas do painel do anunciante (área logada). Montadas em /api/v1/advertiser/ por config/urls_v1.py.

Router próprio: estas views não entram no router do ``core`` nem no
``seedpermissions``; os ``Menu``/``Permission`` saem de ``seed_advertiser_profile``.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from advertiser.modules.import_report.view import AdvertiserImportReportViewSet
from advertiser.modules.inquiry.view import AdvertiserInquiryViewSet
from advertiser.modules.me.view import AdvertiserMeViewSet
from advertiser.modules.property.view import AdvertiserPropertyViewSet
from advertiser.modules.property_request.view import AdvertiserPropertyRequestViewSet
from advertiser.modules.stats.view import AdvertiserStatsViewSet

router = DefaultRouter()
router.register(r"me", AdvertiserMeViewSet, basename="advertiser-me")
router.register(r"properties", AdvertiserPropertyViewSet, basename="advertiser-property")
router.register(r"inquiries", AdvertiserInquiryViewSet, basename="advertiser-inquiry")
router.register(
    r"property-requests", AdvertiserPropertyRequestViewSet, basename="advertiser-property-request"
)
router.register(r"stats", AdvertiserStatsViewSet, basename="advertiser-stats")
router.register(r"import-report", AdvertiserImportReportViewSet, basename="advertiser-import")

urlpatterns = [
    # O router não mapeia PATCH na raiz do prefixo; `me/` precisa de GET + PATCH no mesmo caminho.
    path(
        "me/",
        AdvertiserMeViewSet.as_view({"get": "retrieve_me", "patch": "update_me"}),
        name="advertiser-me-list",
    ),
    *router.urls,
]
