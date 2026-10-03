"""Health check endpoint para load balancers / orquestradores.

Sem autentica\u00e7\u00e3o, sem throttle. Resposta enxuta e barata.
"""

import time

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    # allow-any: endpoint de health-check usado por load balancer / monitoramento.
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(responses={200: dict, 503: dict})
    def get(self, request):
        start = time.time()
        checks = {}

        # 1. Banco responde?
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"fail: {str(e)[:100]}"

        # 2. Tempo total
        checks["response_time_ms"] = int((time.time() - start) * 1000)

        # 3. Algum check falhou?
        all_ok = all(v == "ok" for k, v in checks.items() if k != "response_time_ms")

        return Response(checks, status=200 if all_ok else 503)
