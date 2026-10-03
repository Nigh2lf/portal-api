"""Rotas públicas do site (sem login). Montadas em /api/v1/public/ por config/urls_v1.py.

Router próprio: estas views não entram no router do ``core`` nem no
``seedpermissions`` (não têm ``view_name``/``Menu``).
"""

from rest_framework.routers import DefaultRouter

from public.modules.advertiser.view import PublicAdvertiserViewSet
from public.modules.content.view import PublicPostViewSet, PublicTipViewSet
from public.modules.lead.view import PublicAdvertiserLeadViewSet, PublicContactMessageViewSet, PublicPropertyRequestViewSet
from public.modules.plan.view import PublicAdPlacementViewSet, PublicPlanViewSet
from public.modules.portal.view import PublicPortalViewSet
from public.modules.property.view import PublicPropertyViewSet
from public.modules.register.view import PublicRegisterViewSet

PORTAL = r"portals/(?P<portal_slug>[a-z0-9-]+)"

router = DefaultRouter()
router.register(r"portals", PublicPortalViewSet, basename="public-portal")
router.register(r"plans", PublicPlanViewSet, basename="public-plan")
router.register(r"ad-placements", PublicAdPlacementViewSet, basename="public-ad-placement")
router.register(rf"{PORTAL}/properties", PublicPropertyViewSet, basename="public-property")
router.register(rf"{PORTAL}/advertisers", PublicAdvertiserViewSet, basename="public-advertiser")
router.register(rf"{PORTAL}/posts", PublicPostViewSet, basename="public-post")
router.register(rf"{PORTAL}/tips", PublicTipViewSet, basename="public-tip")
router.register(rf"{PORTAL}/contact-messages", PublicContactMessageViewSet, basename="public-contact-message")
router.register(rf"{PORTAL}/property-requests", PublicPropertyRequestViewSet, basename="public-property-request")
router.register(rf"{PORTAL}/advertiser-leads", PublicAdvertiserLeadViewSet, basename="public-advertiser-lead")
router.register(rf"{PORTAL}/register", PublicRegisterViewSet, basename="public-register")

urlpatterns = router.urls
