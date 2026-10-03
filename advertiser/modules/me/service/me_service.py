from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import Property, User

USER_SYNCED_FIELDS = ("name", "email")


class MeService:
    def __init__(self, advertiser, user):
        self.advertiser = advertiser
        self.user = user

    def update_profile(self, validated_data):
        """
        Atualiza os dados do anunciante e espelha nome/e-mail no usuário de login

        Args:
            validated_data: dados já validados pelo AdvertiserMeUpdateSerializer

        Returns:
            Advertiser
        """
        email = validated_data.get("email")
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise serializers.ValidationError({"email": [_("Já existe um usuário com este e-mail.")]})

        for field, value in validated_data.items():
            setattr(self.advertiser, field, value)
        self.advertiser.updated_by = self.user
        self.advertiser.save()

        synced = [field for field in USER_SYNCED_FIELDS if field in validated_data]
        if synced:
            for field in synced:
                setattr(self.user, field, validated_data[field])
            self.user.save(update_fields=[*synced, "updated_at"])
        return self.advertiser

    def change_password(self, old_password, new_password):
        """
        Troca a senha do usuário de login após conferir a senha atual

        Args:
            old_password: senha atual (como enviada pelo front)
            new_password: nova senha (como enviada pelo front)
        """
        if not self.user.check_password(old_password):
            raise serializers.ValidationError({"old_password": [_("Senha atual incorreta.")]})
        self.user.set_password(new_password)
        self.user.save(update_fields=["password", "updated_at"])
        # TODO: enviar e-mail avisando a troca de senha.

    def plan_usage(self):
        """
        Consumo do plano: imóveis ativos e destaques em uso

        Returns:
            {"properties_used", "featured_used"}
        """
        return Property.objects.filter(advertiser=self.advertiser, deleted_at__isnull=True).aggregate(
            properties_used=Count("id", filter=Q(is_active=True)),
            featured_used=Count("id", filter=Q(is_active=True, is_featured=True)),
        )
