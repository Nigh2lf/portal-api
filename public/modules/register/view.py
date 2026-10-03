from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Portal
from public.modules.register.serializer import PublicRegisterSerializer
from public.modules.register.service import RegisterService


class PublicRegisterViewSet(BaseViewSet):
    # allow-any: cadastro de anunciante pelo site público (pré-login); throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def get_portal(self):
        portal = Portal.objects.filter(slug=self.kwargs.get("portal_slug"), is_active=True).first()
        if portal is None:
            raise NotFound("Portal não encontrado.")
        return portal

    def create(self, request, portal_slug=None):
        """
        Cadastro de anunciante (proprietário, corretor ou imobiliária) com login imediato

        Returns:
            envelope 201 com `{advertiser_id, user_id, is_published, access, refresh}`
        """
        portal = self.get_portal()
        serializer = PublicRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertiser, refresh = RegisterService(portal).register(serializer.validated_data)
        return envelope_success(
            data={
                "advertiser_id": advertiser.pk,
                "user_id": advertiser.user_id,
                "is_published": advertiser.is_published,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            http_status=201,
        )
