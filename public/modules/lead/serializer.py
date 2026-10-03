from rest_framework import serializers

from core.models import PropertyRequest, Purpose


class PublicContactMessageSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=120)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    subject = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    message = serializers.CharField(max_length=4000)
    recaptcha_token = serializers.CharField(required=False, allow_blank=True)


class PublicPropertyRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=120)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    purpose = serializers.ChoiceField(choices=Purpose.choices)
    property_type = serializers.UUIDField(required=False, allow_null=True, default=None)
    city = serializers.UUIDField(required=False, allow_null=True, default=None)
    neighborhood = serializers.UUIDField(required=False, allow_null=True, default=None)
    min_price = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True, default=None, min_value=0)
    max_price = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True, default=None, min_value=0)
    is_in_condominium = serializers.BooleanField(required=False, allow_null=True, default=None)
    funding = serializers.ChoiceField(choices=PropertyRequest.Funding.choices, required=False, allow_blank=True, default="")
    message = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    is_partner_broadcast = serializers.BooleanField(required=False, default=False)
    recaptcha_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        minimo, maximo = attrs.get("min_price"), attrs.get("max_price")
        if minimo is not None and maximo is not None and minimo > maximo:
            raise serializers.ValidationError({"max_price": ["Deve ser maior ou igual ao valor mínimo."]})
        return attrs


class PublicAdvertiserLeadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=120)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    company = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    message = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
