"""Anunciante da sessão: toda view do app parte do usuário logado, nunca de um id do cliente."""

from functools import cached_property

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound

from core.models import Advertiser

MISSING_ADVERTISER_MESSAGE = _("Usuário sem cadastro de anunciante.")


def current_advertiser(request):
    """
    Anunciante vinculado ao usuário autenticado (``user.advertiser_profile``)

    Args:
        request: request autenticada

    Returns:
        Advertiser com plano e portal pré-carregados; 404 se o usuário não é anunciante
    """
    advertiser = (
        Advertiser.objects.select_related("plan", "portal")
        .filter(user_id=request.user.pk, deleted_at__isnull=True)
        .first()
    )
    if advertiser is None:
        raise NotFound(MISSING_ADVERTISER_MESSAGE)
    return advertiser


class CurrentAdvertiserMixin:
    @cached_property
    def advertiser(self):
        return current_advertiser(self.request)
