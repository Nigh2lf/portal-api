from rest_framework import serializers

from core.models import XmlImportError, XmlImportRun


class XmlImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = XmlImportError
        fields = ("id", "property_reference_code", "message", "payload", "created_at")


class XmlImportRunListSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)

    class Meta:
        model = XmlImportRun
        fields = (
            "id",
            "advertiser",
            "advertiser_name",
            "started_at",
            "finished_at",
            "total_properties",
            "valid_properties",
            "invalid_properties",
            "report_email_sent",
            "created_at",
        )


class XmlImportRunDetailSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)
    errors = XmlImportErrorSerializer(many=True, read_only=True)

    class Meta:
        model = XmlImportRun
        fields = (
            "id",
            "advertiser",
            "advertiser_name",
            "started_at",
            "finished_at",
            "total_properties",
            "valid_properties",
            "invalid_properties",
            "report_email_sent",
            "errors",
            "legacy_id",
            "created_at",
            "updated_at",
        )
