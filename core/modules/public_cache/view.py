from django.conf import settings
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import Portal
from core.modules.public_cache.serializer import PublicCacheInvalidateSerializer
from core.services import public_cache


class PublicCacheViewSet(BaseViewSet):
    view_name = "public_cache"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]

    def list(self, request):
        """
        Situação do cache público: escopos, portais e histórico das últimas limpezas

        Returns:
            envelope com `{enabled, backend, site_configured, scopes, portals, history}`
        """
        return envelope_success(
            data={
                "enabled": public_cache.is_enabled(),
                "backend": settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1],
                "site_configured": bool(getattr(settings, "SITE_REVALIDATE_URL", "")),
                "scopes": [{"value": k, "label": v} for k, v in public_cache.SCOPES.items()],
                "portals": list(Portal.objects.filter(is_active=True).order_by("name").values("slug", "name")),
                "history": public_cache.history(),
            }
        )

    @action(detail=False, methods=["post"], url_path="invalidate")
    def invalidate(self, request):
        """
        Limpa o cache público (API e site) por portal, escopo ou código de imóvel

        Returns:
            envelope com `{tags, site: {ok, status, error}|null}`
        """
        serializer = PublicCacheInvalidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        if dados["items"]:
            r = public_cache.invalidate(items=dados["items"], origin="manual", user=request.user.email, wait_site=True)
        else:
            r = public_cache.invalidate(dados["scopes"] or None, dados["portal"] or None, origin="manual", user=request.user.email, wait_site=True)
        return envelope_success(data=r, message="Cache limpo.")
