from rest_framework import serializers

from core.models import RejectedProperty, XmlImportError


class ImportInvalidPropertySerializer(serializers.ModelSerializer):
    reference_code = serializers.CharField(source="property_reference_code", read_only=True)

    class Meta:
        model = RejectedProperty
        fields = ("reference_code", "reason")


class ImportErrorSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = XmlImportError
        fields = ("date", "message")
