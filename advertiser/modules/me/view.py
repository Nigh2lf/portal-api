from django.db import transaction
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from advertiser.modules.me.serializer import (
    AdvertiserMeSerializer,
    AdvertiserMeUpdateSerializer,
    AdvertiserPlanSerializer,
    ChangePasswordSerializer,
)
from advertiser.modules.me.service import MeService
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass


class AdvertiserMeViewSet(CurrentAdvertiserMixin, BaseViewSet):
    view_name = "advertiser_me"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]

    def retrieve_me(self, request):
        """
        Dados do anunciante logado, com plano e portal

        Returns:
            envelope com o anunciante
        """
        return envelope_success(data=self._me_data())

    @transaction.atomic
    def update_me(self, request):
        """
        Atualiza os dados de contato do anunciante (e nome/e-mail do login)

        Returns:
            envelope com o anunciante atualizado
        """
        serializer = AdvertiserMeUpdateSerializer(self.advertiser, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self._service().update_profile(serializer.validated_data)
        return envelope_success(data=self._me_data())

    @action(detail=False, methods=["post"], url_path="change-password")
    @transaction.atomic
    def change_password(self, request):
        """
        Troca a senha do anunciante mediante a senha atual

        Returns:
            envelope com `{ok: true}`
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._service().change_password(**serializer.validated_data)
        return envelope_success(data={"ok": True})

    @action(detail=False, methods=["get"], url_path="plan-usage")
    def plan_usage(self, request):
        """
        Plano contratado e consumo atual (imóveis ativos, destaques, limite de fotos)

        Returns:
            envelope com `{plan, properties_used, featured_used, photo_limit}`
        """
        advertiser = self.advertiser
        return envelope_success(
            data={
                "plan": AdvertiserPlanSerializer(advertiser.plan).data,
                **self._service().plan_usage(),
                "photo_limit": advertiser.effective_photo_limit,
            }
        )

    def _me_data(self):
        return AdvertiserMeSerializer(self.advertiser, context={"request": self.request}).data

    def _service(self) -> MeService:
        return MeService(advertiser=self.advertiser, user=self.request.user)
