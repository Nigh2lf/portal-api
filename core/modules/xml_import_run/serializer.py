from rest_framework import serializers

from core.models import Advertiser, XmlImportBatch, XmlImportError, XmlImportRun


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
            "batch",
            "status",
            "error_message",
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
            "batch",
            "status",
            "error_message",
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


class XmlImportStartSerializer(serializers.Serializer):
    advertiser = serializers.UUIDField()
    simulate = serializers.BooleanField(default=False)


class XmlImportAdvertiserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    legacy_id = serializers.IntegerField(allow_null=True)
    integrator = serializers.CharField(source="integration.integrator.name", default=None)
    xml_url = serializers.CharField(source="integration.xml_url")
    last_imported_at = serializers.DateTimeField(
        source="integration.last_imported_at", allow_null=True
    )


# ------------------------------------------------------------------ lotes


class XmlImportBatchCreateSerializer(serializers.Serializer):
    """``advertisers`` ausente ou nulo = todos os anunciantes com XML ativo."""

    advertisers = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_null=True, allow_empty=False
    )


class XmlImportBatchRunSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source="advertiser.name", read_only=True)

    class Meta:
        model = XmlImportRun
        fields = (
            "id",
            "advertiser",
            "advertiser_name",
            "status",
            "error_message",
            "started_at",
            "finished_at",
            "total_properties",
            "valid_properties",
            "invalid_properties",
        )


class XmlImportBatchSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True, default=None)
    current_advertiser_name = serializers.CharField(
        source="current_advertiser.name", read_only=True, default=None
    )

    class Meta:
        model = XmlImportBatch
        fields = (
            "id",
            "status",
            "origin",
            "scope",
            "total_advertisers",
            "done",
            "ok",
            "failed",
            "skipped",
            "cancelled",
            "current_advertiser",
            "current_advertiser_name",
            "created_by",
            "created_by_name",
            "deadline_at",
            "started_at",
            "finished_at",
            "heartbeat_at",
            "error_message",
            "created_at",
        )


class XmlImportBatchDetailSerializer(XmlImportBatchSerializer):
    """Lote com as execuções já feitas (``runs``) e os anunciantes que ainda vão rodar (``pending``)."""

    runs = serializers.SerializerMethodField()
    pending = serializers.SerializerMethodField()

    class Meta(XmlImportBatchSerializer.Meta):
        fields = (*XmlImportBatchSerializer.Meta.fields, "runs", "pending")

    def get_runs(self, batch):
        qs = batch.runs.select_related("advertiser").order_by("started_at", "created_at")
        return XmlImportBatchRunSerializer(qs, many=True).data

    def get_pending(self, batch):
        done_ids = set(map(str, batch.runs.values_list("advertiser_id", flat=True)))
        pending = [i for i in batch.advertiser_ids if i not in done_ids]
        names = {
            str(pk): name
            for pk, name in Advertiser.objects.filter(pk__in=pending).values_list("id", "name")
        }
        return [{"id": i, "name": names.get(i, "")} for i in pending]
