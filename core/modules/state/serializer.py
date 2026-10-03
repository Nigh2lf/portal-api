from rest_framework import serializers

from core.models import State


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ("id", "code", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_code(self, value):
        return value.strip().upper()


class StateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ("id", "code", "name", "created_at")


class StateDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ("id", "code", "name", "created_at", "updated_at")
