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

from core.views import ProfileViewSet, PublicAssetViewSet, UserViewSet, ViewTokenObtainPair
from core.views.cep import CepLookupView
from core.views.health import HealthCheckView

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"users", UserViewSet, basename="user")
router.register(r"public-assets", PublicAssetViewSet, basename="public-asset")


urlpatterns = [
    path("", include(router.urls)),
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
