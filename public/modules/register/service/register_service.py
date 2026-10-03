import re

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core.models import Advertiser, Plan, Portal, User
from core.modules.auth.serializer import LoginSerializer
from core.services.advertiser_access import grant_advertiser_access
from core.services.slug import unique_slug


def only_digits(value):
    return re.sub(r"\D", "", value or "")


class RegisterService:
    def __init__(self, portal: Portal):
        self.portal = portal

    @transaction.atomic
    def register(self, data):
        """
        Cria o usuário de login, o vínculo ANUNCIANTE e o anunciante do portal

        Args:
            data: dados validados pelo PublicRegisterSerializer

        Returns:
            (Advertiser, RefreshToken) com as mesmas claims do login
        """
        email = User.objects.normalize_email(data["email"].strip().lower())
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": ["Já existe uma conta com este e-mail."]})

        is_owner = data["type"] == Advertiser.Type.OWNER
        plan = self._plan_for(data["plan"], is_owner)

        user = User(email=email, name=data["name"], role=User.Role.USER, is_active=True, is_staff=False)
        user.set_password(data["password"])
        user.save()
        grant_advertiser_access(user)

        advertiser = Advertiser.objects.create(
            user=user,
            portal=self.portal,
            plan=plan,
            type=data["type"],
            name=data["name"],
            slug=unique_slug(Advertiser, data["name"], max_length=140),
            document=data["document"],
            email=email,
            phone=data["phone"],
            phone_secondary=data.get("phone_secondary", ""),
            whatsapp=only_digits(data.get("phone_secondary") or data["phone"]),
            website=data.get("website", ""),
            address=data.get("address", ""),
            creci=data.get("creci", ""),
            contact_name=data.get("contact_name", ""),
            coupon=data.get("coupon", ""),
            # Plano pago entra despublicado até a ativação manual (pagamento); grátis/sob consulta já aparece.
            is_published=not plan.monthly_price,
            accepted_terms_at=timezone.now(),
            has_hotsite=plan.has_hotsite,
            has_realtor_page=plan.has_realtor_page and not is_owner,
            receives_property_requests=plan.receives_property_requests,
            created_by=user,
        )
        # TODO: enviar e-mail de boas-vindas ao anunciante e aviso ao portal via Noclaf.
        return advertiser, LoginSerializer.get_token(user)

    @staticmethod
    def _plan_for(plan_id, is_owner):
        """Plano ativo compatível com o tipo: proprietário só no plano exclusivo e vice-versa."""
        plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
        if plan is None:
            raise serializers.ValidationError({"plan": ["Plano não encontrado."]})
        if is_owner and not plan.is_owner_only:
            raise serializers.ValidationError({"plan": ["Proprietário deve usar o plano exclusivo para proprietários."]})
        if not is_owner and plan.is_owner_only:
            raise serializers.ValidationError({"plan": ["Este plano é exclusivo para proprietários."]})
        return plan
