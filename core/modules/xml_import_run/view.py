from django.db.models import Prefetch
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import XmlImportError, XmlImportRun
from core.modules.xml_import_run.serializer import (
    XmlImportAdvertiserSerializer,
    XmlImportRunDetailSerializer,
    XmlImportRunListSerializer,
    XmlImportStartSerializer,
)
from importacao.services import arquivos
from importacao.services.execucao import anunciantes_com_xml, em_andamento, iniciar_em_segundo_plano


class ImportacaoEmAndamento(APIException):
    status_code = 409
    default_detail = "Já existe uma importação em andamento para este anunciante."
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
        qs = anunciantes_com_xml().order_by("name")
        return envelope_success(data=XmlImportAdvertiserSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        """
        Inicia a importação (ou a simulação) de um anunciante em segundo plano

        Returns:
            envelope com `{started: true}`; 409 se já houver importação rodando para ele
        """
        serializer = XmlImportStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertiser = anunciantes_com_xml().filter(pk=serializer.validated_data["advertiser"]).first()
        if advertiser is None:
            raise ValidationError({"advertiser": ["Anunciante sem XML ativo."]})
        if em_andamento(advertiser):
            raise ImportacaoEmAndamento()
        simular = serializer.validated_data["simulate"]
        iniciar_em_segundo_plano(advertiser.pk, simular=simular)
        return envelope_success(data={"started": True}, message="Simulação iniciada." if simular else "Importação iniciada.", http_status=202)

    @action(detail=False, methods=["get"], url_path="simulation")
    def simulation(self, request):
        """
        Resultado da última simulação do anunciante (`?advertiser=<uuid>`)

        Returns:
            envelope com o resumo e as listas de novos, alterados, excluídos e ignorados; 404 se não houver
        """
        advertiser = anunciantes_com_xml().filter(pk=request.query_params.get("advertiser")).first() if request.query_params.get("advertiser") else None
        if advertiser is None:
            raise ValidationError({"advertiser": ["Informe um anunciante com XML ativo."]})
        dados = arquivos.ler(advertiser.pk, "simulacao.json")
        if dados is None:
            raise NotFound("Nenhuma simulação para este anunciante.")
        return envelope_success(data={**dados, "running": em_andamento(advertiser)})
