"""Rotas da API v1.

Todas ficam montadas em /api/v1/ via config/urls.py.
"""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from core.views import (
    AdPlacementViewSet,
    AdvertiserLeadViewSet,
    AdvertiserViewSet,
    AdViewSet,
    BannerViewSet,
    BlockedSenderViewSet,
    BlogPostViewSet,
    CityViewSet,
    ContactMessageViewSet,
    FeatureViewSet,
    IntegratorViewSet,
    NeighborhoodViewSet,
    PlanViewSet,
    PortalMenuItemViewSet,
    PortalViewSet,
    ProfileViewSet,
    PropertyInquiryViewSet,
    PropertyRequestViewSet,
    PropertyTypeViewSet,
    PropertyViewSet,
    PublicAssetViewSet,
    PublicCacheViewSet,
    RejectedPropertyViewSet,
    ScheduledTaskRunViewSet,
    StateViewSet,
    TipViewSet,
    UserViewSet,
    ViewTokenObtainPair,
    XmlImportRunViewSet,
)
from core.views.cep import CepLookupView
from core.views.health import HealthCheckView

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"users", UserViewSet, basename="user")
router.register(r"public-assets", PublicAssetViewSet, basename="public-asset")

# Catálogos do portal (painel admin)
router.register(r"states", StateViewSet, basename="state")
router.register(r"cities", CityViewSet, basename="city")
router.register(r"neighborhoods", NeighborhoodViewSet, basename="neighborhood")
router.register(r"portal-menu-items", PortalMenuItemViewSet, basename="portal-menu-item")
router.register(r"portals", PortalViewSet, basename="portal")
router.register(r"banners", BannerViewSet, basename="banner")
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"integrators", IntegratorViewSet, basename="integrator")
router.register(r"advertisers", AdvertiserViewSet, basename="advertiser")
router.register(r"property-types", PropertyTypeViewSet, basename="property-type")
router.register(r"features", FeatureViewSet, basename="feature")
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"ad-placements", AdPlacementViewSet, basename="ad-placement")
router.register(r"ads", AdViewSet, basename="ad")
router.register(r"tips", TipViewSet, basename="tip")
router.register(r"blog-posts", BlogPostViewSet, basename="blog-post")
router.register(r"blocked-senders", BlockedSenderViewSet, basename="blocked-sender")
router.register(r"rejected-properties", RejectedPropertyViewSet, basename="rejected-property")

# Leads e históricos (somente leitura/exclusão)
router.register(r"property-inquiries", PropertyInquiryViewSet, basename="property-inquiry")
router.register(r"contact-messages", ContactMessageViewSet, basename="contact-message")
router.register(r"property-requests", PropertyRequestViewSet, basename="property-request")
router.register(r"advertiser-leads", AdvertiserLeadViewSet, basename="advertiser-lead")
router.register(r"xml-import-runs", XmlImportRunViewSet, basename="xml-import-run")
router.register(r"scheduled-task-runs", ScheduledTaskRunViewSet, basename="scheduled-task-run")
router.register(r"public-cache", PublicCacheViewSet, basename="public-cache")


urlpatterns = [
    path("", include(router.urls)),
    path("public/", include("public.urls")),
    path("advertiser/", include("advertiser.urls")),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("cep/<str:cep>/", CepLookupView.as_view(), name="cep-lookup"),
    path("auth/login/", ViewTokenObtainPair.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # OpenAPI schema (controle de acesso configurado em SPECTACULAR_SETTINGS).
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url="/api/v1/schema/"),
        name="schema-swagger-ui",
    ),
    path(
        "docs/redoc/",
        SpectacularRedocView.as_view(url="/api/v1/schema/"),
        name="schema-redoc",
    ),
]
