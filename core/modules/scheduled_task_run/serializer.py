from rest_framework import serializers

from core.models import ScheduledTaskRun


class ScheduledTaskRunListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledTaskRun
        fields = ("id", "name", "status", "started_at", "finished_at", "created_at")


class ScheduledTaskRunDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledTaskRun
        fields = (
            "id",
            "name",
            "status",
            "started_at",
            "finished_at",
            "details",
            "legacy_id",
            "created_at",
            "updated_at",
        )
