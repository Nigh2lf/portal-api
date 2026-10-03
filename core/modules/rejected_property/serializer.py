from rest_framework import serializers

from core.models import RejectedProperty


class RejectedPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = RejectedProperty
        fields = (
            "id",
            "advertiser",
            "property_reference_code",
            "reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RejectedPropertyListSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)

    class Meta:
        model = RejectedProperty
        fields = (
            "id",
            "advertiser",
            "advertiser_name",
            "property_reference_code",
            "reason",
            "created_at",
        )


class RejectedPropertyDetailSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)

    class Meta:
        model = RejectedProperty
        fields = (
            "id",
            "advertiser",
            "advertiser_name",
            "property_reference_code",
            "reason",
            "created_at",
            "updated_at",
        )
