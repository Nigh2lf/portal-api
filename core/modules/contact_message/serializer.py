from rest_framework import serializers

from core.models import ContactMessage


class ContactMessageListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = ContactMessage
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "portal",
            "portal_name",
            "created_at",
        )


class ContactMessageDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = ContactMessage
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "portal",
            "portal_name",
            "ip_address",
            "legacy_id",
            "created_at",
            "updated_at",
        )
