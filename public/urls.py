"""Rotas públicas do site (sem login). Montadas em /api/v1/public/ por config/urls_v1.py.

Router próprio: estas views não entram no router do ``core`` nem no
``seedpermissions`` (não têm ``view_name``/``Menu``).
"""

from rest_framework.routers import DefaultRouter

from public.modules.portal.view import PublicPortalViewSet

router = DefaultRouter()
router.register(r"portals", PublicPortalViewSet, basename="public-portal")

urlpatterns = router.urls
