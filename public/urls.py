"""Rotas públicas do site (sem login). Montadas em /api/v1/public/ por config/urls_v1.py.

Router próprio: estas views não entram no router do ``core`` nem no
``seedpermissions`` (não têm ``view_name``/``Menu``).
"""

from rest_framework.routers import DefaultRouter

from public.modules.advertiser.view import PublicAdvertiserViewSet
from public.modules.portal.view import PublicPortalViewSet
from public.modules.property.view import PublicPropertyViewSet

PORTAL = r"portals/(?P<portal_slug>[a-z0-9-]+)"

router = DefaultRouter()
router.register(r"portals", PublicPortalViewSet, basename="public-portal")
router.register(rf"{PORTAL}/properties", PublicPropertyViewSet, basename="public-property")
router.register(rf"{PORTAL}/advertisers", PublicAdvertiserViewSet, basename="public-advertiser")

urlpatterns = router.urls
