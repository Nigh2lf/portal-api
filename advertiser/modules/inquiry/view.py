import csv

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from advertiser.modules.inquiry.serializer import AdvertiserInquirySerializer
from advertiser.services import CurrentAdvertiserMixin
from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import PropertyInquiry

CSV_HEADER = (
    "Data",
    "Nome",
    "E-mail",
    "Telefone",
    "Código do imóvel",
    "Imóvel",
    "Mensagem",
    "Preferência de contato",
    "Celular",
)


class AdvertiserInquiryViewSet(CurrentAdvertiserMixin, BaseModelViewSet):
    view_name = "advertiser_inquiry"
    router_user = ["USER", "ADMIN"]
    view_read = True
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    http_method_names = ["get", "head", "options"]
    serializer_class = AdvertiserInquirySerializer
    search_fields = ["name", "email", "phone", "property_reference_code", "message"]
    filterset_fields = {"created_at": ["gte", "lte"]}
    ordering_fields = ["name", "email", "created_at"]
    ordering = ("-created_at",)

    def get_queryset(self):
        return PropertyInquiry.objects.filter(advertiser=self.advertiser).select_related(
            "property", "portal"
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """
        Exporta as ofertas filtradas em CSV (UTF-8 com BOM, separador `;`)

        Returns:
            arquivo `ofertas.csv` (sem envelope)
        """
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="ofertas.csv"'
        response.write("﻿")

        writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
        writer.writerow(CSV_HEADER)
        for inquiry in self.filter_queryset(self.get_queryset()).iterator():
            writer.writerow(
                (
                    timezone.localtime(inquiry.created_at).strftime("%d/%m/%Y %H:%M"),
                    inquiry.name,
                    inquiry.email,
                    inquiry.phone,
                    inquiry.property_reference_code,
                    inquiry.property.title if inquiry.property_id else "",
                    inquiry.message,
                    ", ".join(inquiry.contact_preferences or []),
                    "Sim" if inquiry.is_mobile else "Não",
                )
            )
        return response
