from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

MAX_MONTHS = 24


class MonthlyStatsQuerySerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=MAX_MONTHS, default=3)


class PeriodStatsQuerySerializer(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        """Garante `start <= end` quando ambos vierem informados."""
        start, end = attrs.get("start"), attrs.get("end")
        if start and end and start > end:
            raise serializers.ValidationError({"end": [_("A data final deve ser maior ou igual à inicial.")]})
        return attrs
