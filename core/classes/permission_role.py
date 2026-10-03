"""Permissões baseadas no papel de negócio do usuário (``User.role``).

Não confunda com ``is_staff`` (acesso ao Django Admin). Aqui validamos o
papel dentro da API.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from core.models import User


def _denied():
    raise PermissionDenied(
        {
            "success": False,
            "status": 403,
            "message": "Sem permissão para acessar o recurso.",
            "data": {},
            "error": {},
        }
    )


class IsAdminRole(BasePermission):
    """Permite apenas usuários com ``role == User.Role.ADMIN``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            _denied()
        if user.role != User.Role.ADMIN:
            _denied()
        return True


class IsUserRole(BasePermission):
    """Permite apenas usuários com ``role == User.Role.USER``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            _denied()
        if user.role != User.Role.USER:
            _denied()
        return True


class IsAnyRole(BasePermission):
    """Permite qualquer usuário autenticado com um papel reconhecido."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            _denied()
        return user.role in User.Role.values
