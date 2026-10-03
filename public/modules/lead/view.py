from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.models import Portal
from public.modules.lead.serializer import (
    PublicAdvertiserLeadSerializer,
    PublicContactMessageSerializer,
    PublicPropertyRequestSerializer,
)
from public.modules.lead.service import LeadService


class PublicLeadMixin:
    def get_portal(self):
        portal = Portal.objects.filter(slug=self.kwargs.get("portal_slug"), is_active=True).first()
        if portal is None:
            raise NotFound("Portal não encontrado.")
        return portal

    def _validated(self, serializer_class):
        serializer = serializer_class(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def _service(self) -> LeadService:
        return LeadService(self.get_portal(), self.request)


class PublicContactMessageViewSet(PublicLeadMixin, BaseViewSet):
    # allow-any: formulário "Fale conosco" do site público; sem login, throttle por IP e BlockedSender.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def create(self, request, portal_slug=None):
        """
        Mensagem do visitante ao portal ("Fale conosco")

        Returns:
            envelope com `{id}`; 403 se o remetente estiver bloqueado
        """
        service = self._service()
        message = service.create_contact_message(self._validated(PublicContactMessageSerializer))
        return envelope_success(data={"id": message.pk}, http_status=201)


class PublicPropertyRequestViewSet(PublicLeadMixin, BaseViewSet):
    # allow-any: formulário "Encomende seu imóvel" do site público; sem login, throttle por IP e BlockedSender.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def create(self, request, portal_slug=None):
        """
        Encomenda de imóvel do visitante

        Returns:
            envelope com `{id}`; 403 se o remetente estiver bloqueado
        """
        service = self._service()
        pedido = service.create_property_request(self._validated(PublicPropertyRequestSerializer))
        return envelope_success(data={"id": pedido.pk}, http_status=201)


class PublicAdvertiserLeadViewSet(PublicLeadMixin, BaseViewSet):
    # allow-any: formulário "Quero anunciar" do site público; sem login, throttle por IP e BlockedSender.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def create(self, request, portal_slug=None):
        """
        Interesse em anunciar no portal (lead comercial)

        Returns:
            envelope com `{id}`; 403 se o remetente estiver bloqueado
        """
        service = self._service()
        lead = service.create_advertiser_lead(self._validated(PublicAdvertiserLeadSerializer))
        return envelope_success(data={"id": lead.pk}, http_status=201)
