from django.db.models import Prefetch
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import XmlImportBatch, XmlImportError, XmlImportRun
from core.modules.xml_import_run.serializer import (
    XmlImportAdvertiserSerializer,
    XmlImportBatchCreateSerializer,
    XmlImportBatchDetailSerializer,
    XmlImportBatchSerializer,
    XmlImportRunDetailSerializer,
    XmlImportRunListSerializer,
    XmlImportStartSerializer,
)
from xml_import.services import files
from xml_import.services.batches import (
    BatchNotCancellable,
    EmptyBatch,
    active_batch,
    advertiser_queue,
    advertisers_in_active_batches,
    cancel_batch,
    create_batch,
    start_batch_in_background,
)
from xml_import.services.execution import advertisers_with_xml, in_progress, start_in_background

UUID_RE = r"[0-9a-fA-F-]{36}"
RECENT_BATCHES = 20


class ImportacaoEmAndamento(APIException):
    status_code = 409
    default_detail = "Já existe uma importação em andamento para este anunciante."
    default_code = "conflict"


class LoteEmAndamento(APIException):
    status_code = 409
    default_detail = "Um ou mais anunciantes já estão em um lote em andamento."
    default_code = "conflict"


class LoteJaEncerrado(APIException):
    status_code = 409
    default_detail = "Este lote não está na fila nem em execução."
    default_code = "conflict"


class XmlImportRunViewSet(BaseModelViewSet):
    view_name = "xml_import_run"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "post", "delete", "head", "options"]
    serializer_class = XmlImportRunDetailSerializer
    search_fields = ["advertiser__name"]
    filterset_fields = {
        "advertiser": ["exact"],
        "batch": ["exact"],
        "status": ["exact"],
        "report_email_sent": ["exact"],
        "started_at": ["gte", "lte"],
    }
    ordering_fields = ["started_at", "finished_at", "total_properties", "invalid_properties"]
    ordering = ("-started_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return XmlImportRunListSerializer
        return XmlImportRunDetailSerializer

    def get_queryset(self):
        queryset = XmlImportRun.objects.select_related("advertiser")
        if self.action == "list":
            return queryset
        return queryset.prefetch_related(
            Prefetch("errors", queryset=XmlImportError.objects.order_by("created_at"))
        )

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=False, methods=["get"], url_path="advertisers")
    def advertisers(self, request):
        """
        Anunciantes com XML ativo, com a data da última importação

        Returns:
            envelope com `[{id, name, legacy_id, integrator, xml_url, last_imported_at}]`
        """
        qs = advertisers_with_xml().order_by("name")
        return envelope_success(data=XmlImportAdvertiserSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        """
        Inicia a simulação de um anunciante em segundo plano, ou a importação (como lote de um anunciante)

        Returns:
            envelope com `{started: true, batch: <id|null>}`; 409 se já houver importação rodando para ele
        """
        serializer = XmlImportStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertiser = (
            advertisers_with_xml().filter(pk=serializer.validated_data["advertiser"]).first()
        )
        if advertiser is None:
            raise ValidationError({"advertiser": ["Anunciante sem XML ativo."]})
        if in_progress(advertiser) or str(advertiser.pk) in advertisers_in_active_batches():
            raise ImportacaoEmAndamento()
        if serializer.validated_data["simulate"]:
            start_in_background(advertiser.pk, simulate=True)
            return envelope_success(
                data={"started": True, "batch": None},
                message="Simulação iniciada.",
                http_status=202,
            )
        batch = create_batch(advertiser_ids=[advertiser.pk], user=request.user)
        start_batch_in_background(batch.pk)
        return envelope_success(
            data={"started": True, "batch": str(batch.pk)},
            message="Importação iniciada.",
            http_status=202,
        )

    @action(detail=False, methods=["get"], url_path="simulation")
    def simulation(self, request):
        """
        Resultado da última simulação do anunciante (`?advertiser=<uuid>`)

        Returns:
            envelope com o resumo e as listas de novos, alterados, excluídos e ignorados; 404 se não houver
        """
        advertiser = (
            advertisers_with_xml().filter(pk=request.query_params.get("advertiser")).first()
            if request.query_params.get("advertiser")
            else None
        )
        if advertiser is None:
            raise ValidationError({"advertiser": ["Informe um anunciante com XML ativo."]})
        dados = files.read(advertiser.pk, "simulacao.json")
        if dados is None:
            raise NotFound("Nenhuma simulação para este anunciante.")
        return envelope_success(data={**dados, "running": in_progress(advertiser)})

    # ------------------------------------------------------------------ batches

    @action(detail=False, methods=["get", "post"], url_path="batches")
    def batches(self, request):
        """
        GET: os últimos lotes. POST: cria e inicia um lote em segundo plano

        Body do POST: `{advertisers: [uuid, ...]}` ou sem `advertisers` para todos os advertisers com XML ativo.

        Returns:
            GET: envelope com a lista dos lotes recentes. POST: 202 com o lote criado; 409 se algum
            dos advertisers já estiver em um lote ativo
        """
        if request.method == "GET":
            qs = XmlImportBatch.objects.select_related("current_advertiser", "created_by").order_by(
                "-created_at"
            )[:RECENT_BATCHES]
            return envelope_success(data=XmlImportBatchSerializer(qs, many=True).data)

        serializer = XmlImportBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data.get("advertisers")
        if ids is not None:
            _, invalid = advertiser_queue(ids)
            if invalid:
                raise ValidationError({"advertisers": [f"Sem XML ativo: {', '.join(invalid)}"]})
        requested = (
            {str(i) for i in ids}
            if ids is not None
            else {str(a.pk) for a in advertisers_with_xml()}
        )
        busy = requested & advertisers_in_active_batches()
        if busy:
            raise LoteEmAndamento()
        try:
            batch = create_batch(advertiser_ids=ids, user=request.user)
        except EmptyBatch as exc:
            raise ValidationError({"advertisers": [str(exc)]}) from exc
        start_batch_in_background(batch.pk)
        return envelope_success(
            data=XmlImportBatchDetailSerializer(batch).data,
            message=f"Importação de {batch.total_advertisers} anunciante(s) iniciada.",
            http_status=202,
        )

    @action(detail=False, methods=["get"], url_path="batches/active")
    def active_batch(self, request):
        """
        O batch em andamento (ou na fila), com progresso, execuções feitas e advertisers pending

        Returns:
            envelope com o lote, ou `null` se nenhum estiver ativo
        """
        batch = active_batch()
        return envelope_success(data=XmlImportBatchDetailSerializer(batch).data if batch else None)

    @action(detail=False, methods=["get"], url_path=f"batches/(?P<batch_id>{UUID_RE})")
    def batch_detail(self, request, batch_id=None):
        """
        Um batch com suas execuções e os advertisers pending

        Returns:
            envelope com o lote; 404 se não existir
        """
        return envelope_success(data=XmlImportBatchDetailSerializer(self._get_batch(batch_id)).data)

    @action(detail=False, methods=["post"], url_path=f"batches/(?P<batch_id>{UUID_RE})/cancel")
    def cancel_batch(self, request, batch_id=None):
        """
        Cancela o lote: na fila, cancela na hora; em execução, para no próximo ponto seguro

        Returns:
            envelope com o lote atualizado; 409 se ele já terminou
        """
        batch = self._get_batch(batch_id)
        try:
            batch = cancel_batch(batch)
        except BatchNotCancellable as exc:
            raise LoteJaEncerrado() from exc
        message = (
            "Lote cancelado."
            if batch.status == XmlImportBatch.Status.CANCELLED
            else "Cancelamento solicitado; o lote para no próximo anunciante."
        )
        return envelope_success(data=XmlImportBatchDetailSerializer(batch).data, message=message)

    @staticmethod
    def _get_batch(batch_id):
        batch = (
            XmlImportBatch.objects.select_related("current_advertiser", "created_by")
            .filter(pk=batch_id)
            .first()
        )
        if batch is None:
            raise NotFound("Lote não encontrado.")
        return batch
