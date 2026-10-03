from rest_framework import serializers

from core.models import Integrator


class IntegratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integrator
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class IntegratorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integrator
        fields = ("id", "name", "slug", "is_active", "created_at")


class IntegratorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integrator
        fields = ("id", "name", "slug", "is_active", "legacy_id", "created_at", "updated_at")
