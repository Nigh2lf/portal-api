"""Consulta pública de CEP via API da Noclaf.

Este endpoint NÃO exige autenticação do usuário final (front-end consome
direto), mas é throttled (`scope='cep'`) para proteger nossa cota na Noclaf.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.classes.exception_handler import envelope_success
from core.services import lookup_cep


class _CepResponseSerializer(serializers.Serializer):
    """Stub apenas para o drf-spectacular gerar schema. Não é usado em runtime."""

    cep = serializers.CharField()
    logradouro = serializers.CharField(allow_blank=True)
    bairro = serializers.CharField(allow_blank=True)
    cidade = serializers.CharField(allow_blank=True)
    uf = serializers.CharField(allow_blank=True)


class CepLookupView(APIView):
    """GET /api/v1/cep/<cep>/ — consulta pública (com throttle)."""

    # allow-any: lookup pblico para autocompletar endereo no front; throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cep"
    serializer_class = _CepResponseSerializer

    @extend_schema(
        parameters=[OpenApiParameter("cep", str, OpenApiParameter.PATH)],
        responses={200: _CepResponseSerializer, 400: dict, 503: dict},
    )
    def get(self, request, cep: str) -> Response:
        data, error = lookup_cep(cep)
        if error is not None:
            return Response(
                {
                    "success": False,
                    "status": error.status,
                    "message": error.message,
                    "data": None,
                    "error": {"detail": error.message},
                },
                status=error.status,
            )
        return envelope_success(data=data, http_status=200)
