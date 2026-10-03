from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import BlockedSender


class BlockedSenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSender
        fields = (
            "id",
            "email",
            "ip_address",
            "reason",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        email = attrs.get("email", getattr(self.instance, "email", ""))
        ip_address = attrs.get("ip_address", getattr(self.instance, "ip_address", None))
        if not email and not ip_address:
            raise serializers.ValidationError(
                {"email": [_("Informe ao menos o e-mail ou o IP a bloquear.")]}
            )
        return attrs


class BlockedSenderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSender
        fields = ("id", "email", "ip_address", "reason", "is_active", "created_at")


class BlockedSenderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSender
        fields = (
            "id",
            "email",
            "ip_address",
            "reason",
            "is_active",
            "legacy_id",
            "created_at",
            "updated_at",
        )
