from rest_framework import serializers

from core.models import AdvertiserLead


class AdvertiserLeadListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = AdvertiserLead
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "company",
            "portal",
            "portal_name",
            "created_at",
        )


class AdvertiserLeadDetailSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = AdvertiserLead
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "company",
            "message",
            "portal",
            "portal_name",
            "legacy_id",
            "created_at",
            "updated_at",
        )
