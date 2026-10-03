"""Thread-local que guarda o ``request.user`` atual para os signals de auditoria.

Signals (`post_save`, `post_delete`) não recebem o request, então o middleware
abaixo armazena o usuário em uma variável de contexto por thread/asyncio.
Em fluxos sem request (shell, management commands, jobs) o usuário é ``None``.
"""

from __future__ import annotations

from contextvars import ContextVar

from django.utils.deprecation import MiddlewareMixin

_current_user: ContextVar = ContextVar("current_user", default=None)


def get_current_user():
    """Retorna o usuário autenticado da request em curso, ou ``None``."""
    user = _current_user.get()
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user


def set_current_user(user) -> None:
    _current_user.set(user)


class CurrentUserMiddleware(MiddlewareMixin):
    """Popula o ``ContextVar`` com o ``request.user`` em cada request."""

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        token = _current_user.set(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(token)
