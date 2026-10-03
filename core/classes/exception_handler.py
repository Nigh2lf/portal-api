"""Exception handler global do DRF que padroniza o envelope de resposta.

Formato:
    {
        "success": bool,
        "status": int,
        "message": str,
        "data": dict | list | None,
        "error": dict | list | None,
    }

Configurado em settings: REST_FRAMEWORK['EXCEPTION_HANDLER'].
"""

import logging

from django.conf import settings
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _default_message_for(exc):
    if isinstance(exc, ValidationError):
        return _("Dados inválidos.")
    if isinstance(exc, NotAuthenticated | AuthenticationFailed):
        return _("Autenticação necessária.")
    if isinstance(exc, PermissionDenied):
        return _("Sem permissão para acessar o recurso.")
    if isinstance(exc, NotFound | Http404):
        return _("Recurso não encontrado.")
    if isinstance(exc, Throttled):
        return _("Muitas requisições. Tente novamente mais tarde.")
    if isinstance(exc, APIException):
        return str(exc.default_detail)
    return _("Erro interno no servidor.")


def envelope_exception_handler(exc, context):
    """Encapsula qualquer exceção do DRF no envelope padrão."""
    response = drf_exception_handler(exc, context)

    if response is None:
        # Exceção não tratada pelo DRF (ex.: erro Python puro) -> 500.
        logger.exception("Unhandled exception", exc_info=exc)
        message = str(exc) if settings.DEBUG else _("Erro interno no servidor.")
        return Response(
            {
                "success": False,
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": message,
                "data": None,
                "error": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    payload = response.data
    message = _default_message_for(exc)

    # ValidationError: mantém o detalhe completo em "error" para o front.
    error = payload if isinstance(payload, dict | list) else {"detail": payload}

    response.data = {
        "success": False,
        "status": response.status_code,
        "message": str(message),
        "data": None,
        "error": error,
    }
    return response


def envelope_success(data=None, message="", http_status=status.HTTP_200_OK):
    """Helper para responses de sucesso no mesmo formato."""
    return Response(
        {
            "success": True,
            "status": http_status,
            "message": str(message),
            "data": data,
            "error": None,
        },
        status=http_status,
    )
