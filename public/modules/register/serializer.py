import re

from rest_framework import serializers

from core.models import Advertiser

DOCUMENT_LENGTHS = (11, 14)


class PublicRegisterSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=Advertiser.Type.choices)
    plan = serializers.UUIDField()
    name = serializers.CharField(max_length=120)
    document = serializers.CharField(max_length=20)
    email = serializers.EmailField(max_length=120)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    phone = serializers.CharField(max_length=30)
    phone_secondary = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    contact_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    website = serializers.URLField(max_length=200, required=False, allow_blank=True, default="")
    address = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    creci = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    coupon = serializers.CharField(max_length=45, required=False, allow_blank=True, default="")
    accepted_terms = serializers.BooleanField()

    def validate_document(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) not in DOCUMENT_LENGTHS:
            raise serializers.ValidationError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")
        return digits

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError("É preciso aceitar os Termos de Uso.")
        return value
