from rest_framework import serializers

from core.models import AdvertiserLead, City, ContactMessage, Neighborhood, Portal, PropertyRequest, PropertyType
from public.services.sender import client_ip, ensure_sender_allowed


class LeadService:
    def __init__(self, portal: Portal, request):
        self.portal = portal
        self.ip = client_ip(request)

    def create_contact_message(self, data):
        """
        Grava a mensagem do "Fale conosco" do portal

        Args:
            data: dados validados pelo PublicContactMessageSerializer

        Returns:
            ContactMessage
        """
        ensure_sender_allowed(data["email"], self.ip)
        message = ContactMessage.objects.create(
            portal=self.portal,
            name=data["name"],
            email=data["email"],
            phone=data.get("phone", ""),
            subject=data.get("subject", ""),
            message=data["message"],
            ip_address=self.ip,
        )
        # TODO: enviar e-mail ao portal via Noclaf (core/services/services_emails.py).
        return message

    def create_property_request(self, data):
        """
        Grava a encomenda de imóvel do visitante (sem anunciante; pode ser repassada aos parceiros)

        Args:
            data: dados validados pelo PublicPropertyRequestSerializer

        Returns:
            PropertyRequest
        """
        ensure_sender_allowed(data["email"], self.ip)
        request = PropertyRequest.objects.create(
            portal=self.portal,
            advertiser=None,
            name=data["name"],
            email=data["email"],
            phone=data.get("phone", ""),
            purpose=data["purpose"],
            property_type=self._resolve(PropertyType, data.get("property_type"), "property_type", "Tipo de imóvel não encontrado."),
            city=self._resolve(City, data.get("city"), "city", "Cidade não encontrada."),
            neighborhood=self._resolve(Neighborhood, data.get("neighborhood"), "neighborhood", "Bairro não encontrado."),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            is_in_condominium=data.get("is_in_condominium"),
            funding=data.get("funding", ""),
            message=data.get("message", ""),
            is_partner_broadcast=data.get("is_partner_broadcast", False),
            ip_address=self.ip,
        )
        # TODO: enviar e-mail ao portal e, se `is_partner_broadcast`, aos anunciantes com `receives_property_requests` (Noclaf).
        return request

    def create_advertiser_lead(self, data):
        """
        Grava o interesse em anunciar (página "Anunciar" / landing B2B)

        Args:
            data: dados validados pelo PublicAdvertiserLeadSerializer

        Returns:
            AdvertiserLead
        """
        ensure_sender_allowed(data["email"], self.ip)
        lead = AdvertiserLead.objects.create(
            portal=self.portal,
            name=data["name"],
            email=data["email"],
            phone=data.get("phone", ""),
            company=data.get("company", ""),
            message=data.get("message", ""),
        )
        # TODO: enviar e-mail comercial ao portal via Noclaf.
        return lead

    @staticmethod
    def _resolve(model, pk, field, not_found_message):
        """Resolve o UUID opcional em registro ativo; 400 no campo quando não existe."""
        if pk is None:
            return None
        obj = model.objects.filter(pk=pk, is_active=True).first()
        if obj is None:
            raise serializers.ValidationError({field: [not_found_message]})
        return obj
